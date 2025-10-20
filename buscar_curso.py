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
PREDIO_REFERENCIA = "Quata 200"
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
    dia_semana: Optional[str] = None

    def exibir_formatado(self) -> str:
        """Retorna string formatada para WhatsApp"""
        return f"""📚 *{self.curso}*
📍 Sala: {self.sala}
🏢 Prédio: {self.predio}
👨‍🏫 Professor: {self.professor}
🕐 {self.horario_inicio} - {self.horario_termino}"""


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
                
                aula = AulaCurso(
                    curso=turma,
                    sala=sala,
                    predio=predio,
                    professor=professor,
                    horario_inicio=hora_inicio,
                    horario_termino=hora_termino
                )
                
                aulas_encontradas.append(aula)
                
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
        Dicionário com horários ocupados por curso
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
                
                if turma not in horarios_ocupados:
                    horarios_ocupados[turma] = set()
                horarios_ocupados[turma].add((hora_inicio, hora_termino))
                
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
        for curso_sala, horarios_sala in sorted(horarios_sala_referencia.items()):
            resultado += f"{curso_sala}:\n"
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


# ============================================================================
# FUNÇÃO PRINCIPAL
# ============================================================================
def main():
    """Função principal"""
    # Buscar XML
    xml_content = buscar_xml_com_retry(XML_URL)
    if not xml_content:
        return
    
    # Buscar aulas do curso específico
    aulas = buscar_curso_no_xml(xml_content, CURSO_BUSCADO)
    
    if not aulas:
        print(f"❌ Nenhuma aula encontrada para: {CURSO_BUSCADO}")
        return
    
    # Buscar horários em que a sala de referência está ocupada (excluindo o curso buscado)
    horarios_ocupados = buscar_horarios_sala_referencia(
        xml_content, SALA_REFERENCIA, PREDIO_REFERENCIA, CURSO_BUSCADO
    )
    
    # Exibir aulas do curso com análise completa
    print(formatar_todas_aulas(
        aulas,
        horarios_ocupados,
        xml_content,
        PREDIO_REFERENCIA,
        SALA_REFERENCIA
    ))
    
    if not horarios_ocupados:
        print(f"\nℹ️ A sala {SALA_REFERENCIA} está livre em todo o período (ou ocupada apenas por {CURSO_BUSCADO})")
        return


if __name__ == "__main__":
    main()