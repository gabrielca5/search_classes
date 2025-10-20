## search-classes — busca de salas disponíveis

> Utilitário Python para busca inteligente de cursos, salas disponíveis e gerenciamento de horários no Insper.

## Principais funcionalidades

- 🔍 **Buscar cursos** - encontre todas as aulas de um curso específico
- 🏫 **Salas livres** - localize salas disponíveis em um intervalo de tempo
- 👥 **Comparar horários** - encontre horários em comum entre múltiplos cursos
- 📊 **Relatório de disponibilidade** - visualize quais salas estão livres em cada horário
- 💡 **Sugestões inteligentes** - receba recomendações de salas alternativas
- 🚨 **Alertas de conflito** - seja notificado sobre conflitos de horários

## Saída

Os dados são formatados de forma clara e pronta para copiar no WhatsApp, com:
- Lista de aulas com professor, sala e horário
- Resumo do dia (total de aulas, professores, horários)
- Análise de conflitos
- Sugestões de salas alternativas
- Relatório de disponibilidade

## Requisitos

- Python 3.10+
- Dependências em `requirements.txt`

## Como usar

1. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

2. **Execute o programa:**

```bash
python buscar_curso.py
```

3. **Escolha uma opção do menu:**
   - Buscar curso
   - Encontrar salas livres
   - Comparar horários de cursos
   - Relatório de disponibilidade

## Configuração

Edite as constantes no início do arquivo para customizar:

```python
XML_URL = "https://cgi.insper.edu.br/Agenda/xml/ExibeCalendario.xml"
CURSO_BUSCADO = "2º CIÊNCIA DA COMPUTAÇÃO A"
SALA_REFERENCIA = "513"
PREDIO_REFERENCIA = "Quata 200"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15
```

## Estrutura do projeto

```
search_classes/
├── buscar_curso.py       # Script principal com todas as funcionalidades
├── requirements.txt      # Dependências do projeto
├── README.md            # Este arquivo
└── output/              # Pasta para arquivos gerados (se aplicável)
```

## Tecnologias

- `requests` - requisições HTTP
- `BeautifulSoup` - parsing de XML
- `openpyxl` - geração de arquivos Excel (se necessário)

## Licença

MIT


