"""
Sistema de Busca de Curso Específico - Insper
Autor: Sistema Automatizado
Data: 2025-10-20
Descrição: Busca informações de um curso específico (sala, endereço, professor, horário)
"""

import logging
from datetime import datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

# Configuração de logging - apenas para erros críticos
logging.basicConfig(
    level=logging.ERROR,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================
XML_URL = "https://cgi.insper.edu.br/Agenda/xml/ExibeCalendario.xml"
CURSO_BUSCADO = "2º CIÊNCIA DA COMPUTAÇÃO A"
SALA_REFERENCIA = "513"
PREDIO_REFERENCIA = "PRÉDIO QUATÁ 200"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15


# ============================================================================
# MODELOS DE DADOS
# ============================================================================
@dataclass
class AulaCurso:
    """Modelo de dados para aula de um curso"""
    curso: str
    sala: str
    predio: str
    professor: str
    horario_inicio: str
    horario_termino: str
    aula: Optional[str] = None
    dia_semana: Optional[str] = None

    def exibir_formatado(self) -> str:
        """Retorna string formatada para WhatsApp"""
        return f"""📚 *{self.curso}*
📍 Sala: {self.sala}
🏢 Prédio: {self.predio}
👤 Professor: {self.professor}
📖 Aula: {self.aula if self.aula else "N/A"}
⏰ {self.horario_inicio} - {self.horario_termino}"""


# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================
def buscar_xml_com_retry(url: str, max_tentativas: int = MAX_RETRIES) -> Optional[bytes]:
    """Busca o conteúdo XML com retry"""
    for tentativa in range(1, max_tentativas + 1):
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            if tentativa == max_tentativas:
                logger.error(f"Falha ao obter dados: {e}")
                return None
    return None


# ============================================================================
# FUNÇÃO DE BUSCA
# ============================================================================
def buscar_curso_no_xml(xml_content: bytes, curso_buscado: str) -> List[AulaCurso]:
    """
    Busca todas as ocorrências de um curso no XML
    
    Args:
        xml_content: Conteúdo do XML em bytes
        curso_buscado: Nome do curso a buscar
        
    Returns:
        Lista de aulas encontradas
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")
    
    aulas_encontradas: List[AulaCurso] = []
    eventos = soup.find_all("CalendarioEvento")
    
    for evento in eventos:
        try:
            turma = evento.find("turma").text.strip()
            
            # Verificar se é o curso buscado
            if turma.upper() == curso_buscado.upper():
                sala = evento.find("sala").text.strip()
                predio = evento.find("predio").text.strip()
                professor = evento.find("professor").text.strip()
                hora_inicio = evento.find("horainicio").text.strip()
                hora_termino = evento.find("horatermino").text.strip()
                
                # Buscar titulo em vez de aula
                titulo = evento.find("titulo")
                titulo_text = titulo.text.strip() if titulo else None
                
                aula_obj = AulaCurso(
                    curso=turma,
                    sala=sala,
                    predio=predio,
                    professor=professor,
                    horario_inicio=hora_inicio,
                    horario_termino=hora_termino,
                    aula=titulo_text
                )
                
                aulas_encontradas.append(aula_obj)
                
        except (AttributeError, KeyError):
            continue
    
    return aulas_encontradas


def buscar_horarios_sala_referencia(xml_content: bytes, sala: str, predio: str, curso_excluir: str) -> Dict[str, Set[str]]:
    """
    Busca todos os horários em que a sala de referência está ocupada (excluindo o curso específico)
    
    Args:
        xml_content: Conteúdo do XML em bytes
        sala: Número da sala
        predio: Nome do prédio
        curso_excluir: Curso a excluir da busca
        
    Returns:
        Dicionário com horários ocupados por curso e aula
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")
    horarios_ocupados: Dict[str, Set[str]] = {}
    eventos = soup.find_all("CalendarioEvento")
    
    for evento in eventos:
        try:
            sala_evento = evento.find("sala").text.strip()
            predio_evento = evento.find("predio").text.strip()
            turma = evento.find("turma").text.strip()
            
            if sala_evento == sala and predio_evento == predio and turma.upper() != curso_excluir.upper():
                hora_inicio = evento.find("horainicio").text.strip()
                hora_termino = evento.find("horatermino").text.strip()
                
                # Buscar titulo em vez de aula
                titulo = evento.find("titulo")
                titulo_text = titulo.text.strip() if titulo else ""
                
                # Criar chave com curso e título
                chave_curso = f"{turma} - {titulo_text}" if titulo_text else turma
                
                if chave_curso not in horarios_ocupados:
                    horarios_ocupados[chave_curso] = set()
                horarios_ocupados[chave_curso].add((hora_inicio, hora_termino))
                
        except (AttributeError, KeyError):
            continue
    
    return horarios_ocupados


def buscar_salas_livres(xml_content: bytes, predio: str, horarios_bloqueados: Set[tuple]) -> List[Dict]:
    """
    Busca todas as salas do prédio que estão livres nos horários bloqueados
    
    Args:
        xml_content: Conteúdo do XML em bytes
        predio: Nome do prédio
        horarios_bloqueados: Conjunto de tuplas (hora_inicio, hora_termino) bloqueadas
        
    Returns:
        Lista com informações das salas livres
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")
    salas_predio: Dict[str, Set[tuple]] = {}
    eventos = soup.find_all("CalendarioEvento")
    
    # Mapear todas as salas e seus horários ocupados
    for evento in eventos:
        try:
            sala_evento = evento.find("sala").text.strip()
            predio_evento = evento.find("predio").text.strip()
            
            if predio_evento == predio:
                hora_inicio = evento.find("horainicio").text.strip()
                hora_termino = evento.find("horatermino").text.strip()
                
                if sala_evento not in salas_predio:
                    salas_predio[sala_evento] = set()
                salas_predio[sala_evento].add((hora_inicio, hora_termino))
                
        except (AttributeError, KeyError):
            continue
    
    # Encontrar salas livres nos horários bloqueados
    salas_livres = []
    for sala, horarios_ocupados in salas_predio.items():
        # Verificar se a sala está 100% livre em TODOS os horários bloqueados
        sala_livre = True
        for horario_bloqueado in horarios_bloqueados:
            if horario_bloqueado in horarios_ocupados:
                sala_livre = False
                break
        
        # Apenas adicionar se a sala estiver completamente livre
        if sala_livre:
            for horario_bloqueado in horarios_bloqueados:
                salas_livres.append({
                    'sala': sala,
                    'predio': predio,
                    'horario_inicio': horario_bloqueado[0],
                    'horario_termino': horario_bloqueado[1]
                })
    
    return salas_livres


def gerar_resumo_dia(aulas: List[AulaCurso]) -> str:
    """
    Gera um resumo das aulas do dia
    
    Args:
        aulas: Lista de aulas encontradas
        
    Returns:
        String com resumo formatado
    """
    if not aulas:
        return ""
    
    # Calcular estatísticas
    total_aulas = len(aulas)
    professores = set(aula.professor for aula in aulas)
    total_professores = len(professores)
    horarios = sorted(set((aula.horario_inicio, aula.horario_termino) for aula in aulas))
    
    primeiro_horario = horarios[0][0] if horarios else "N/A"
    ultimo_horario = horarios[-1][1] if horarios else "N/A"
    
    resultado = "📊 *RESUMO DO DIA*\n"
    resultado += "─" * 50 + "\n"
    resultado += f"Total de aulas: {total_aulas}\n"
    resultado += f"Professores envolvidos: {total_professores}\n"
    resultado += f"Primeiro horário: {primeiro_horario}\n"
    resultado += f"Último horário: {ultimo_horario}\n"
    
    return resultado


def gerar_alerta_conflito_sala(sala: str, predio: str, horarios_ocupados: Dict[str, Set[tuple]]) -> str:
    """
    Gera alerta sobre conflito de sala
    
    Args:
        sala: Número da sala
        predio: Nome do prédio
        horarios_ocupados: Dicionário com horários ocupados
        
    Returns:
        String com alerta formatado
    """
    if not horarios_ocupados:
        return ""
    
    resultado = f"🚨 *ATENÇÃO:* Sala {sala} está sendo usada por outro(s) curso(s):\n"
    resultado += "─" * 50 + "\n"
    
    for curso, horarios in sorted(horarios_ocupados.items()):
        resultado += f"• {curso}:\n"
        for h_inicio, h_termino in sorted(horarios):
            resultado += f"   {h_inicio} - {h_termino}\n"
    
    resultado += "\nVerifique possíveis conflitos antes de ir!\n"
    
    return resultado


def sugerir_salas_alternativas(
    xml_content: bytes,
    predio: str,
    horarios_bloqueados: Set[tuple],
    salas_excluir: Set[str],
    max_sugestoes: int = 3
) -> str:
    """
    Sugere salas alternativas livres
    
    Args:
        xml_content: Conteúdo do XML
        predio: Nome do prédio
        horarios_bloqueados: Horários a verificar
        salas_excluir: Salas a excluir das sugestões
        max_sugestoes: Número máximo de sugestões
        
    Returns:
        String com sugestões formatadas
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")
    salas_livres_por_horario: Dict[tuple, List[str]] = {}
    
    # Para cada horário bloqueado, encontrar salas livres
    for h_inicio, h_termino in horarios_bloqueados:
        salas_predio: Dict[str, Set[tuple]] = {}
        eventos = soup.find_all("CalendarioEvento")
        
        for evento in eventos:
            try:
                sala_evento = evento.find("sala").text.strip()
                predio_evento = evento.find("predio").text.strip()
                
                if predio_evento == predio:
                    hora_inicio = evento.find("horainicio").text.strip()
                    hora_termino = evento.find("horatermino").text.strip()
                    
                    if sala_evento not in salas_predio:
                        salas_predio[sala_evento] = set()
                    salas_predio[sala_evento].add((hora_inicio, hora_termino))
                    
            except (AttributeError, KeyError):
                continue
        
        # Encontrar salas livres neste horário
        todas_salas = set(sala for sala, _ in salas_predio.items())
        salas_ocupadas_neste_horario = {
            sala for sala, horarios in salas_predio.items()
            if (h_inicio, h_termino) in horarios
        }
        
        salas_livres = sorted(list(
            todas_salas - salas_ocupadas_neste_horario - salas_excluir
        ))
        
        salas_livres_por_horario[(h_inicio, h_termino)] = salas_livres
    
    # Gerar sugestões
    resultado = ""
    sugestoes_adicionadas = 0
    
    for (h_inicio, h_termino), salas_livres in salas_livres_por_horario.items():
        if salas_livres and sugestoes_adicionadas < max_sugestoes:
            resultado += f"💡 *SUGESTÃO* - {h_inicio} a {h_termino}:\n"
            for sala in salas_livres[:2]:  # Mostrar até 2 salas por horário
                resultado += f"   Sala {sala} está livre\n"
            resultado += "\n"
            sugestoes_adicionadas += 1
    
    return resultado


def gerar_relatorio_disponibilidade_horarios(
    xml_content: bytes,
    predio: str,
    horarios_bloqueados: Set[tuple]
) -> str:
    """
    Gera relatório de disponibilidade para os horários específicos
    
    Args:
        xml_content: Conteúdo do XML
        predio: Nome do prédio
        horarios_bloqueados: Horários para verificar
        
    Returns:
        String com relatório formatado
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")
    resultado = ""
    
    for h_inicio, h_termino in sorted(horarios_bloqueados):
        salas_predio: Dict[str, Set[tuple]] = {}
        eventos = soup.find_all("CalendarioEvento")
        
        for evento in eventos:
            try:
                sala_evento = evento.find("sala").text.strip()
                predio_evento = evento.find("predio").text.strip()
                
                if predio_evento == predio:
                    hora_inicio = evento.find("horainicio").text.strip()
                    hora_termino = evento.find("horatermino").text.strip()
                    
                    if sala_evento not in salas_predio:
                        salas_predio[sala_evento] = set()
                    salas_predio[sala_evento].add((hora_inicio, hora_termino))
                    
            except (AttributeError, KeyError):
                continue
        
        # Contar salas livres
        todas_salas = set(sala for sala, _ in salas_predio.items())
        salas_ocupadas = {
            sala for sala, horarios in salas_predio.items()
            if (h_inicio, h_termino) in horarios
        }
        
        salas_livres_count = len(todas_salas - salas_ocupadas)
        salas_ocupadas_count = len(salas_ocupadas)
        
        if salas_livres_count > 0:
            resultado += f"🟢 *{h_inicio} - {h_termino}*\n"
            resultado += f"   {salas_livres_count} salas disponíveis | "
            resultado += f"{salas_ocupadas_count} ocupadas\n\n"
        else:
            resultado += f"🔴 *{h_inicio} - {h_termino}*\n"
            resultado += f"   Todas as salas ocupadas\n\n"
    
    return resultado


def formatar_todas_aulas(
    aulas: List[AulaCurso],
    horarios_sala_referencia: Dict[str, Set[tuple]] = None,
    xml_content: bytes = None,
    predio: str = None,
    sala_referencia: str = None
) -> str:
    """
    Formata todas as aulas em uma única string para WhatsApp com análise completa
    
    Args:
        aulas: Lista de aulas encontradas
        horarios_sala_referencia: Dicionário com horários da sala de referência
        xml_content: Conteúdo do XML para análises
        predio: Nome do prédio
        sala_referencia: Sala de referência
        
    Returns:
        String com todas as aulas formatadas
    """
    if not aulas:
        return ""
    
    # Obter data atual
    data_atual = datetime.now().strftime("%d/%m/%Y")
    separador = "═" * 60
    
    resultado = f"📋 *AULAS - {data_atual}*\n"
    resultado += separador + "\n\n"
    
    # Adicionar aulas PRIMEIRO
    for idx, aula in enumerate(aulas, 1):
        resultado += f"{idx}. *{aula.curso}*\n"
        resultado += f"   📍 Sala: {aula.sala}\n"
        resultado += f"   🏢 Prédio: {aula.predio}\n"
        resultado += f"   👤 Professor: {aula.professor}\n"
        if aula.aula:
            resultado += f"   📖 Aula: {aula.aula}\n"
        resultado += f"   ⏰ Horário: {aula.horario_inicio} - {aula.horario_termino}\n"
        
        if idx < len(aulas):
            resultado += "\n"
    
    resultado += "\n" + separador + "\n\n"
    
    # Adicionar resumo do dia
    resultado += "📊 *RESUMO DO DIA*\n"
    resultado += separador + "\n"
    
    total_aulas = len(aulas)
    professores = set(aula.professor for aula in aulas)
    total_professores = len(professores)
    horarios = sorted(set((aula.horario_inicio, aula.horario_termino) for aula in aulas))
    primeiro_horario = horarios[0][0] if horarios else "N/A"
    ultimo_horario = horarios[-1][1] if horarios else "N/A"
    
    resultado += f"Total de aulas: {total_aulas}\n"
    resultado += f"Professores envolvidos: {total_professores}\n"
    resultado += f"Primeiro horário: {primeiro_horario}\n"
    resultado += f"Último horário: {ultimo_horario}\n"
    resultado += "\n" + separador + "\n\n"
    
    # Adicionar horários da sala de referência se existirem conflitos
    if horarios_sala_referencia:
        resultado += f"📌 *SALA {sala_referencia} NESTES HORÁRIOS*\n"
        resultado += separador + "\n"
        for curso_aula, horarios_sala in sorted(horarios_sala_referencia.items()):
            resultado += f"{curso_aula}:\n"
            for h_inicio, h_termino in sorted(horarios_sala):
                resultado += f"   {h_inicio} - {h_termino}\n"
        resultado += "\n" + separador + "\n\n"
    
    # Adicionar alerta se houver conflitos
    if horarios_sala_referencia:
        resultado += f"🚨 *ATENÇÃO:* Sala {sala_referencia} está sendo usada por outro(s) curso(s)\n"
        resultado += separador + "\n"
        resultado += "Verifique possíveis conflitos antes de ir!\n"
        resultado += "\n" + separador + "\n\n"
    
    # Adicionar sugestões e disponibilidade
    if xml_content and predio and sala_referencia and horarios_sala_referencia:
        horarios_bloqueados: Set[tuple] = set()
        for horarios_sala in horarios_sala_referencia.values():
            horarios_bloqueados.update(horarios_sala)
        
        # Sugestões
        sugestoes = sugerir_salas_alternativas(
            xml_content, predio, horarios_bloqueados, {sala_referencia}
        )
        if sugestoes:
            resultado += "💡 *SUGESTÕES DE SALAS ALTERNATIVAS*\n"
            resultado += separador + "\n"
            resultado += sugestoes
            resultado += separador + "\n\n"
        
        # Disponibilidade
        resultado += "📊 *DISPONIBILIDADE NOS HORÁRIOS*\n"
        resultado += separador + "\n"
        
        soup = BeautifulSoup(xml_content, "lxml-xml")
        
        for h_inicio, h_termino in sorted(horarios_bloqueados):
            salas_predio: Dict[str, Set[tuple]] = {}
            eventos = soup.find_all("CalendarioEvento")
            
            for evento in eventos:
                try:
                    sala_evento = evento.find("sala").text.strip()
                    predio_evento = evento.find("predio").text.strip()
                    
                    if predio_evento == predio:
                        hora_inicio = evento.find("horainicio").text.strip()
                        hora_termino = evento.find("horatermino").text.strip()
                        
                        if sala_evento not in salas_predio:
                            salas_predio[sala_evento] = set()
                        salas_predio[sala_evento].add((hora_inicio, hora_termino))
                        
                except (AttributeError, KeyError):
                    continue
            
            # Contar salas livres
            todas_salas = set(sala for sala, _ in salas_predio.items())
            salas_ocupadas = {
                sala for sala, horarios_h in salas_predio.items()
                if (h_inicio, h_termino) in horarios_h
            }
            
            salas_livres_count = len(todas_salas - salas_ocupadas)
            salas_ocupadas_count = len(salas_ocupadas)
            
            if salas_livres_count > 0:
                resultado += f"🟢 {h_inicio} - {h_termino}\n"
                resultado += f"   {salas_livres_count} livres | {salas_ocupadas_count} ocupadas\n\n"
            else:
                resultado += f"🔴 {h_inicio} - {h_termino}\n"
                resultado += f"   Todas as salas ocupadas\n\n"
        
        resultado += separador
    
    return resultado.strip()


def buscar_todas_aulas_sala(xml_content: bytes, sala: str, predio: str) -> List[AulaCurso]:
    """Busca TODAS as aulas de uma sala específica"""
    soup = BeautifulSoup(xml_content, "lxml-xml")
    aulas_sala: List[AulaCurso] = []
    eventos = soup.find_all("CalendarioEvento")
    
    for evento in eventos:
        try:
            sala_evento = evento.find("sala").text.strip()
            predio_evento = evento.find("predio").text.strip()
            
            if sala_evento == sala and predio_evento == predio:
                turma = evento.find("turma").text.strip()
                professor = evento.find("professor").text.strip()
                hora_inicio = evento.find("horainicio").text.strip()
                hora_termino = evento.find("horatermino").text.strip()
                titulo = evento.find("titulo")
                titulo_text = titulo.text.strip() if titulo else None
                
                aula_obj = AulaCurso(
                    curso=turma,
                    sala=sala,
                    predio=predio,
                    professor=professor,
                    horario_inicio=hora_inicio,
                    horario_termino=hora_termino,
                    aula=titulo_text
                )
                aulas_sala.append(aula_obj)
                
        except (AttributeError, KeyError):
            continue
    
    return aulas_sala


def buscar_todas_aulas_do_dia(xml_content: bytes) -> List[AulaCurso]:
    """
    Busca TODAS as aulas que ocorrem no dia
    
    Args:
        xml_content: Conteúdo do XML em bytes
        
    Returns:
        Lista com todas as aulas do dia
    """
    soup = BeautifulSoup(xml_content, "lxml-xml")
    todas_aulas: List[AulaCurso] = []
    eventos = soup.find_all("CalendarioEvento")
    
    for evento in eventos:
        try:
            turma = evento.find("turma").text.strip()
            sala = evento.find("sala").text.strip()
            predio = evento.find("predio").text.strip()
            professor = evento.find("professor").text.strip()
            hora_inicio = evento.find("horainicio").text.strip()
            hora_termino = evento.find("horatermino").text.strip()
            titulo = evento.find("titulo")
            titulo_text = titulo.text.strip() if titulo else None
            
            aula_obj = AulaCurso(
                curso=turma,
                sala=sala,
                predio=predio,
                professor=professor,
                horario_inicio=hora_inicio,
                horario_termino=hora_termino,
                aula=titulo_text
            )
            todas_aulas.append(aula_obj)
            
        except (AttributeError, KeyError):
            continue
    
    return todas_aulas


def formatar_relatorio_completo(
    aulas: List[AulaCurso],
    todas_aulas_sala: List[AulaCurso],
    todas_aulas_dia: List[AulaCurso],
    xml_content: bytes,
    predio: str,
    sala_referencia: str
) -> str:
    """
    Formata relatório COMPLETO:
    1. Aulas do curso buscado
    2. Todas as aulas da sala de referência
    3. TODAS as aulas do dia
    4. Análises e sugestões
    """
    data_atual = datetime.now().strftime("%d/%m/%Y")
    sep_grande = "═" * 70
    sep_pequeno = "─" * 70
    
    resultado = f"📋 *RELATÓRIO COMPLETO - {data_atual}*\n"
    resultado += sep_grande + "\n\n"
    
    # ========== SEÇÃO 1: AULAS DO CURSO BUSCADO ==========
    resultado += f"🎓 *AULAS DE {CURSO_BUSCADO}*\n"
    resultado += sep_pequeno + "\n\n"
    
    for idx, aula in enumerate(aulas, 1):
        resultado += f"{idx}. {aula.horario_inicio} - {aula.horario_termino}\n"
        resultado += f"   📍 Sala: {aula.sala}\n"
        resultado += f"   🏢 Prédio: {aula.predio}\n"
        resultado += f"   👤 Professor: {aula.professor}\n"
        if aula.aula:
            resultado += f"   📖 {aula.aula}\n"
        resultado += "\n"
    
    resultado += sep_grande + "\n\n"
    
    # ========== SEÇÃO 2: TODAS AS AULAS NA SALA DE REFERÊNCIA ==========
    if todas_aulas_sala:
        resultado += f"📌 *TODAS AS AULAS NA SALA {sala_referencia}*\n"
        resultado += sep_pequeno + "\n\n"
        
        aulas_por_horario: Dict[tuple, List[AulaCurso]] = {}
        for aula in todas_aulas_sala:
            chave = (aula.horario_inicio, aula.horario_termino)
            if chave not in aulas_por_horario:
                aulas_por_horario[chave] = []
            aulas_por_horario[chave].append(aula)
        
        for (h_inicio, h_termino), aulas_neste_horario in sorted(aulas_por_horario.items()):
            resultado += f"⏰ *{h_inicio} - {h_termino}*\n"
            for aula in aulas_neste_horario:
                if aula.curso.upper() == CURSO_BUSCADO.upper():
                    resultado += f"   ✓ {aula.curso} (SEU CURSO)\n"
                else:
                    resultado += f"   • {aula.curso}\n"
                resultado += f"     Prof: {aula.professor}\n"
            resultado += "\n"
        
        resultado += sep_grande + "\n\n"
    
    # ========== SEÇÃO 3: TODAS AS AULAS DO DIA ==========
    resultado += f"📅 *TODAS AS AULAS DO DIA*\n"
    resultado += sep_pequeno + "\n\n"
    
    aulas_por_horario_dia: Dict[tuple, List[AulaCurso]] = {}
    for aula in todas_aulas_dia:
        chave = (aula.horario_inicio, aula.horario_termino)
        if chave not in aulas_por_horario_dia:
            aulas_por_horario_dia[chave] = []
        aulas_por_horario_dia[chave].append(aula)
    
    for (h_inicio, h_termino), aulas_neste_horario in sorted(aulas_por_horario_dia.items()):
        resultado += f"⏰ *{h_inicio} - {h_termino}*\n"
        for aula in sorted(aulas_neste_horario, key=lambda x: x.sala):
            resultado += f"   • {aula.curso}\n"
            resultado += f"     Sala: {aula.sala} | Prof: {aula.professor}\n"
        resultado += "\n"
    
    resultado += sep_grande + "\n\n"
    
    # ========== SEÇÃO 4: RESUMO ==========
    resultado += "📊 *RESUMO*\n"
    resultado += sep_pequeno + "\n\n"
    
    aulas_outros_cursos = [aula for aula in todas_aulas_sala 
                           if aula.curso.upper() != CURSO_BUSCADO.upper()]
    
    resultado += f"Aulas do seu curso: {len(aulas)}\n"
    resultado += f"Total de aulas na sala {sala_referencia}: {len(todas_aulas_sala)}\n"
    resultado += f"Total de aulas do dia: {len(todas_aulas_dia)}\n"
    resultado += f"Aulas de outros cursos na sala: {len(aulas_outros_cursos)}\n\n"
    
    if aulas_outros_cursos:
        resultado += f"🚨 *CONFLITOS DETECTADOS:* {len(aulas_outros_cursos)} aula(s) de outro(s) curso(s) na sala {sala_referencia}\n"
    else:
        resultado += f"✅ *SEM CONFLITOS:* Sala {sala_referencia} é exclusiva para seu curso!\n"
    
    resultado += "\n" + sep_grande
    
    return resultado


def formatar_horarios_sala_e_curso(
    todas_aulas_sala: List[AulaCurso],
    aulas_curso: List[AulaCurso],
    sala: str,
    curso: str
) -> str:
    """
    Formata todos os horários da sala e do curso em um único relatório
    
    Args:
        todas_aulas_sala: Todas as aulas da sala de referência
        aulas_curso: Todas as aulas do curso buscado
        sala: Número da sala
        curso: Nome do curso
        
    Returns:
        String com formatação de horários
    """
    data_atual = datetime.now().strftime("%d/%m/%Y")
    sep = "═" * 70
    
    resultado = f"📋 *HORÁRIOS - {data_atual}*\n"
    resultado += sep + "\n\n"
    
    # ========== SEÇÃO 1: TODOS OS HORÁRIOS DA SALA ==========
    resultado += f"📍 *TODOS OS HORÁRIOS DA SALA {sala}*\n"
    resultado += "─" * 70 + "\n\n"
    
    if todas_aulas_sala:
        aulas_por_horario: Dict[tuple, List[AulaCurso]] = {}
        for aula in todas_aulas_sala:
            chave = (aula.horario_inicio, aula.horario_termino)
            if chave not in aulas_por_horario:
                aulas_por_horario[chave] = []
            aulas_por_horario[chave].append(aula)
        
        for (h_inicio, h_termino), aulas_neste_horario in sorted(aulas_por_horario.items()):
            resultado += f"⏰ *{h_inicio} - {h_termino}*\n"
            for aula in aulas_neste_horario:
                resultado += f"   • {aula.curso}\n"
                resultado += f"     Prof: {aula.professor}\n"
                if aula.aula:
                    resultado += f"     {aula.aula}\n"
            resultado += "\n"
    else:
        resultado += "Nenhuma aula encontrada para esta sala.\n\n"
    
    resultado += sep + "\n\n"
    
    # ========== SEÇÃO 2: TODOS OS HORÁRIOS DO CURSO ==========
    resultado += f"🎓 *TODOS OS HORÁRIOS DO CURSO {curso}*\n"
    resultado += "─" * 70 + "\n\n"
    
    if aulas_curso:
        aulas_curso_por_horario: Dict[tuple, List[AulaCurso]] = {}
        for aula in aulas_curso:
            chave = (aula.horario_inicio, aula.horario_termino)
            if chave not in aulas_curso_por_horario:
                aulas_curso_por_horario[chave] = []
            aulas_curso_por_horario[chave].append(aula)
        
        for (h_inicio, h_termino), aulas_neste_horario in sorted(aulas_curso_por_horario.items()):
            resultado += f"⏰ *{h_inicio} - {h_termino}*\n"
            for aula in aulas_neste_horario:
                resultado += f"   Sala: {aula.sala}\n"
                resultado += f"   Prof: {aula.professor}\n"
                resultado += f"   Prédio: {aula.predio}\n"
                if aula.aula:
                    resultado += f"   {aula.aula}\n"
            resultado += "\n"
    else:
        resultado += "Nenhuma aula encontrada para este curso.\n\n"
    
    resultado += sep
    
    return resultado


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================
def main():
    """Função principal"""
    xml_content = buscar_xml_com_retry(XML_URL)
    if not xml_content:
        return
    
    # Buscar aulas do curso específico
    aulas_curso = buscar_curso_no_xml(xml_content, CURSO_BUSCADO)
    
    # Buscar todas as aulas da sala de referência
    todas_aulas_sala = buscar_todas_aulas_sala(
        xml_content, SALA_REFERENCIA, PREDIO_REFERENCIA
    )
    
    # Exibir apenas o relatório de horários da sala e do curso
    print(formatar_horarios_sala_e_curso(
        todas_aulas_sala,
        aulas_curso,
        SALA_REFERENCIA,
        CURSO_BUSCADO
    ))


if __name__ == "__main__":
    main()