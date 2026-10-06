import json
import re
import os
import subprocess
import urllib.request
import urllib.error
import time


# =========================================================
# CONFIGURAÇÕES
# =========================================================

NOTION_ENABLED = os.environ.get("NOTION_ENABLED", "true").lower() == "true"
TOKEN = os.environ.get("NOTION_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

VERSION = "2025-09-03"

DATA_SOURCE = os.environ.get(
    "NOTION_DATA_SOURCE",
    "d4190e15-cd71-4d55-8706-1ccfeb0227fd"
)

GROQ_MODEL = os.environ.get(
    "GROQ_MODEL",
    "openai/gpt-oss-20b"
)

MIN_SCORE = float(
    os.environ.get("AI_DEVOPS_MIN_SCORE", "0")
)

FAIL_ON_HIGH_RISK = (
    os.environ.get("AI_DEVOPS_FAIL_ON_HIGH_RISK", "false").lower()
    == "true"
)

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY não configurado.")

if NOTION_ENABLED and not TOKEN:
    raise RuntimeError(
        "NOTION_TOKEN não configurado enquanto NOTION_ENABLED=true."
    )


# =========================================================
# INFORMAÇÕES DO GITHUB ACTIONS
# =========================================================

SHA = os.environ["COMMIT_SHA"]

BEFORE = os.environ["BEFORE_SHA"]

MESSAGE = os.environ.get(
    "COMMIT_MESSAGE",
    ""
)

AUTHOR = os.environ.get(
    "COMMIT_AUTHOR",
    "Desconhecido"
)

DATE = os.environ.get(
    "COMMIT_DATE",
    ""
)

REPO = os.environ["REPOSITORY"]

REPO_URL = os.environ["REPOSITORY_URL"]

COMMIT_URL = os.environ["COMMIT_URL"]

EVENT_NAME = os.environ.get("GITHUB_EVENT_NAME", "unknown")
PR_NUMBER = os.environ.get("PR_NUMBER", "")

PROJECT = REPO.split(
    "/",
    1
)[1]


# =========================================================
# EXECUTAR COMANDOS GIT
# =========================================================

def git(*args):

    return subprocess.check_output(
        ["git", *args],
        text=True,
        stderr=subprocess.DEVNULL
    ).strip()


def read_text_file(path, limit=5000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as file:
            return file.read()[:limit]
    except (OSError, UnicodeError):
        return ""


def project_context():
    candidates = [
        "README.md",
        "README",
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "pom.xml",
        "build.gradle",
        "go.mod",
        "Cargo.toml",
        "composer.json",
        "Gemfile",
        "Dockerfile",
        "docker-compose.yml",
        "tsconfig.json",
    ]

    sections = []

    for path in candidates:
        content = read_text_file(path)

        if content:
            sections.append(
                f"===== {path} =====\n{content}"
            )

    context = "\n\n".join(sections)

    return context[:8000]


PROJECT_CONTEXT = project_context()


# =========================================================
# API DO NOTION
# =========================================================

def notion(
    method,
    path,
    body=None
):

    data = (
        None
        if body is None
        else json.dumps(body).encode()
    )

    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",

        data=data,

        method=method,

        headers={
            "Authorization": f"Bearer {TOKEN}",

            "Notion-Version": VERSION,

            "Content-Type": "application/json",

            "User-Agent":
                "github-actions-groq-notion/1.0",
        },
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode()
            )

    except urllib.error.HTTPError as error:

        details = error.read().decode(
            errors="replace"
        )

        raise RuntimeError(
            f"Notion API {error.code}: {details}"
        )


# =========================================================
# GROQ — ENGINE DE CODE REVIEW
# =========================================================

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "categoria": {
            "type": "string",
            "enum": [
                "✨ Feature",
                "🐛 Correção",
                "📚 Documentação",
                "♻️ Refatoração",
                "🧪 Teste",
                "🔐 Segurança",
                "⚡ Performance",
                "🔧 Manutenção",
                "📝 Alteração"
            ]
        },
        "resumo_executivo": {"type": "string"},
        "o_que_foi_alterado": {"type": "string"},
        "como_funciona": {"type": "string"},
        "impacto": {"type": "string"},
        "pontos_fortes": {
            "type": "array",
            "items": {"type": "string"}
        },
        "compatibilidade": {"type": "string"},
        "regressao": {"type": "string"},
        "performance": {"type": "string"},
        "seguranca": {"type": "string"},
        "testes": {"type": "string"},
        "melhorias": {"type": "string"},
        "problemas_encontrados": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severidade": {
                        "type": "string",
                        "enum": ["Baixa", "Média", "Alta"]
                    },
                    "problema": {"type": "string"},
                    "arquivo": {"type": "string"},
                    "linha": {"type": "string"},
                    "evidencia": {"type": "string"},
                    "sugestao": {"type": "string"},
                    "confianca": {"type": "number"}
                },
                "required": [
                    "severidade",
                    "problema",
                    "arquivo",
                    "linha",
                    "evidencia",
                    "sugestao",
                    "confianca"
                ],
                "additionalProperties": False
            }
        },
        "qualidade": {"type": "number"},
        "seguranca_nota": {"type": "number"},
        "manutenibilidade": {"type": "number"},
        "risco": {
            "type": "string",
            "enum": ["Baixo", "Médio", "Alto"]
        },
        "confianca_geral": {"type": "number"},
        "arquivos_principais": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": [
        "categoria",
        "resumo_executivo",
        "o_que_foi_alterado",
        "como_funciona",
        "impacto",
        "pontos_fortes",
        "compatibilidade",
        "regressao",
        "performance",
        "seguranca",
        "testes",
        "melhorias",
        "problemas_encontrados",
        "qualidade",
        "seguranca_nota",
        "manutenibilidade",
        "risco",
        "confianca_geral",
        "arquivos_principais"
    ],
    "additionalProperties": False
}


SYSTEM_PROMPT = """
Você é o AI DevOps Reviewer de uma plataforma profissional de engenharia
de software.

Seu trabalho é analisar mudanças de código com rigor de code review sênior,
segurança de aplicações, testes, manutenção, arquitetura e engenharia de
software.

PRINCÍPIO CENTRAL: EVIDÊNCIA ANTES DE OPINIÃO.

Você só pode afirmar algo como fato quando existir evidência suficiente no
commit, diff, arquivos alterados ou contexto do projeto fornecido.

NUNCA:
- invente funcionalidades;
- invente arquivos;
- invente linhas;
- invente vulnerabilidades;
- invente testes executados;
- invente resultados de testes;
- afirme que o código compilou sem evidência;
- afirme que uma vulnerabilidade existe apenas porque "poderia existir";
- transforme uma possibilidade em certeza;
- trate ausência de evidência como prova de segurança;
- recomende uma mudança apenas por preferência pessoal;
- critique código que não foi alterado sem explicar claramente por que ele
  é diretamente afetado pela alteração.

QUANDO HOUVER INCERTEZA:
- diga explicitamente que não é possível determinar;
- reduza a confiança;
- não transforme hipótese em problema confirmado.

REGRA ESPECIAL PARA PYTHON:
Quando o código analisado estiver dentro de uma f-string Python, {{ e }}
podem ser escapes intencionais para produzir { e } literais.
NÃO confunda isso com Jinja, erro de sintaxe ou código inválido.
Só classifique como erro se o contexto real do código sustentar essa conclusão.

REGRA DE LINHAS:
Só informe uma linha quando ela puder ser sustentada pelo diff.
Caso contrário, use "N/A".

SEGURANÇA:
Analise, quando houver evidência:
- exposição de segredos;
- autenticação e autorização;
- injeção;
- execução arbitrária;
- validação de entrada;
- manipulação insegura de dados;
- permissões;
- criptografia;
- logs com dados sensíveis;
- SSRF;
- XSS;
- SQL injection;
- command injection;
- path traversal;
- desserialização insegura;
- dependências/configurações claramente perigosas.

Não faça checklist cego. Só reporte uma categoria quando houver evidência
relevante.

BUGS:
Procure inconsistências de lógica, estados impossíveis, erros de fluxo,
tratamento de exceções, valores nulos, limites, concorrência e regressões
quando o diff fornecer evidência suficiente.

TESTES:
Não diga que testes foram executados se eles não aparecem nas evidências.
Separe claramente:
- testes observados no diff;
- testes recomendados.

NOTAS:
0–10.
As notas devem refletir SOMENTE a alteração analisada.
Não use 0 como valor padrão.
Uma alteração simples e correta pode ter nota alta.
Uma alteração incompleta ou arriscada deve receber nota proporcional.

RISCO:
Baixo = mudança localizada e sem impacto perigoso evidente.
Médio = mudança com possibilidade razoável de regressão ou impacto relevante.
Alto = evidência de defeito grave, vulnerabilidade grave ou alteração crítica.

CONFIANÇA:
0.0–1.0.
Alta confiança somente quando a evidência é direta e suficiente.

QUALIDADE DO REVIEW:
Se não houver problema real, NÃO invente um problema para preencher a lista.
Use "Nenhum problema evidente no diff.".

Escreva em português do Brasil, com linguagem profissional, objetiva e
tecnicamente precisa.
"""


def groq(prompt):
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.1,
        "reasoning_effort": "medium",
        "max_tokens": 1800,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "professional_code_review",
                "strict": True,
                "schema": REVIEW_SCHEMA
            }
        }
    }

    data = json.dumps(body, ensure_ascii=False).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "ai-devops/2.0"
        }
    )

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            print(
                f"🤖 AI DevOps → Groq | modelo={GROQ_MODEL} | "
                f"tentativa={attempt}/{max_attempts}"
            )

            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(
                    response.read().decode()
                )

            content = (
                result["choices"][0]["message"]["content"]
                .strip()
            )

            if not content:
                raise RuntimeError(
                    "A Groq retornou uma resposta vazia."
                )

            analysis = json.loads(content)

            print("✅ Review estruturado recebido da Groq.")

            return analysis

        except urllib.error.HTTPError as error:
            details = error.read().decode(errors="replace")

            if error.code in (
                429, 500, 502, 503, 504
            ) and attempt < max_attempts:
                retry_after = error.headers.get(
                    "retry-after"
                )

                try:
                    wait_seconds = max(
                        5,
                        int(float(retry_after))
                    ) + 2
                except (TypeError, ValueError):
                    wait_seconds = 22

                print(
                    f"⚠️ Groq retornou HTTP {error.code}. "
                    f"Aguardando {wait_seconds}s conforme o rate limit..."
                )

                time.sleep(wait_seconds)
                continue

            raise RuntimeError(
                f"Groq API {error.code}: {details}"
            )

        except (
            json.JSONDecodeError,
            KeyError,
            TypeError,
            RuntimeError
        ) as error:
            if attempt < max_attempts:
                print(
                    f"⚠️ Resposta inválida da Groq: {error}. "
                    "Tentando novamente..."
                )
                time.sleep(attempt * 2)
                continue

            raise RuntimeError(
                f"Falha ao obter review estruturado: {error}"
            )


# =========================================================
# BLOCOS DO NOTION
# =========================================================

def block(
    kind,
    content
):

    content = str(
        content
    )

    return {

        "object": "block",

        "type": kind,

        kind: {

            "rich_text": [

                {

                    "type": "text",

                    "text": {

                        # O Notion limita rich_text
                        # a 2000 caracteres por bloco.
                        "content":
                            content[:2000]
                    }
                }
            ]
        },
    }


def paragraph(
    content
):

    return block(
        "paragraph",
        content
    )


def bullet(
    content
):

    return block(
        "bulleted_list_item",
        content
    )


def heading(
    level,
    content
):

    return block(
        f"heading_{level}",
        content
    )


# =========================================================
# FUNÇÕES AUXILIARES DA IA
# =========================================================

def clean_list(
    value
):

    if not isinstance(
        value,
        list
    ):

        return []


    return [

        str(item).strip()

        for item in value

        if str(item).strip()

    ]


def score(
    value,
    fallback=None
):

    # Aceita números, "8.5/10", "8,5/10" e textos
    # que contenham uma nota entre 0 e 10.
    if isinstance(value, bool):
        return fallback

    try:
        number = float(value)
        return max(0.0, min(10.0, number))
    except (TypeError, ValueError):
        pass

    if value is not None:
        text_value = str(value).strip().replace(",", ".")
        match = re.search(
            r"(?<!\\d)(10(?:\\.0+)?|[0-9](?:\\.[0-9]+)?)(?:\\s*/\\s*10)?",
            text_value
        )

        if match:
            try:
                number = float(match.group(1))
                return max(0.0, min(10.0, number))
            except ValueError:
                pass

    return fallback


# =========================================================
# DESCOBRIR COMMIT ANTERIOR
# =========================================================

zero = "0" * 40


if BEFORE != zero:

    try:

        git(
            "cat-file",
            "-e",
            f"{BEFORE}^{{commit}}"
        )

        base = BEFORE


    except subprocess.CalledProcessError:

        base = git(
            "rev-parse",
            f"{SHA}^"
        )


else:

    base = git(
        "rev-parse",
        f"{SHA}^"
    )


# =========================================================
# ARQUIVOS ALTERADOS
# =========================================================

raw_files = git(

    "diff",

    "--name-status",

    base,

    SHA
)


files = [

    line.split(
        "\t",
        1
    )

    for line in raw_files.splitlines()

    if "\t" in line
]


# =========================================================
# ESTATÍSTICAS
# =========================================================

raw_stats = git(

    "diff",

    "--numstat",

    base,

    SHA
)


added = 0

deleted = 0


for line in raw_stats.splitlines():

    parts = line.split(
        "\t"
    )


    if len(parts) >= 2:

        try:

            added += int(
                parts[0]
            )

            deleted += int(
                parts[1]
            )

        except ValueError:

            pass


# =========================================================
# DIFF DO COMMIT
# =========================================================

try:

    diff = git(

        "diff",

        "--no-ext-diff",

        "--unified=3",

        base,

        SHA
    )


except subprocess.CalledProcessError:

    diff = ""


# Evita enviar diffs gigantes para a IA.

MAX_DIFF = 12000


if len(diff) > MAX_DIFF:

    diff = diff[:MAX_DIFF] + (

        "\n\n"
        "[DIFF TRUNCADO AUTOMATICAMENTE]"
        "\n"
    )


# =========================================================
# CLASSIFICAÇÃO INICIAL
# =========================================================

kind = "📝 Alteração"


for prefix, label in [

    (
        "feat:",
        "✨ Feature"
    ),

    (
        "fix:",
        "🐛 Correção"
    ),

    (
        "docs:",
        "📚 Documentação"
    ),

    (
        "refactor:",
        "♻️ Refatoração"
    ),

    (
        "test:",
        "🧪 Teste"
    ),

    (
        "chore:",
        "🔧 Manutenção"
    ),

]:

    if MESSAGE.strip().lower().startswith(
        prefix
    ):

        kind = label

        break


# =========================================================
# CONTEXTO ENVIADO À IA
# =========================================================

prompt = f"""
Faça uma revisão profissional e baseada em evidências do commit abaixo.

IMPORTANTE:
- O diff é a fonte primária da análise.
- O contexto do projeto serve apenas para compreender a arquitetura e o
  propósito da alteração.
- Não assuma que arquivos não mostrados foram alterados.
- Não invente resultados de execução.
- Não confunda hipótese com problema confirmado.
- Não considere {{ e }} dentro de uma f-string Python um erro por si só.

PROJETO:
{PROJECT}

REPOSITÓRIO:
{REPO}

EVENTO:
{EVENT_NAME}

COMMIT:
{SHA}

AUTOR:
{AUTHOR}

DATA:
{DATE}

MENSAGEM:
{MESSAGE}

ESTATÍSTICAS:
Arquivos alterados: {len(files)}
Linhas adicionadas: {added}
Linhas removidas: {deleted}

ARQUIVOS ALTERADOS:
{chr(10).join(
    f"- {status}: {path}"
    for status, path in files[:100]
)}

CONTEXTO DO PROJETO:
{PROJECT_CONTEXT}

DIFF:
{diff}

REGRAS DE DECISÃO:

1. Primeiro entenda o que mudou.
2. Depois determine o efeito técnico.
3. Depois procure problemas concretos.
4. Para cada problema, exija evidência.
5. Se não houver evidência suficiente, não reporte o problema como fato.
6. Se não houver problemas, declare isso explicitamente.
7. Avalie segurança somente com base no que pode ser sustentado.
8. Recomendações devem ser acionáveis e relacionadas à alteração.
9. As notas devem ser coerentes e independentes entre si.
10. A confiança deve refletir a quantidade e qualidade das evidências.
11. Não use linguagem sensacionalista.
12. Não inclua o diff inteiro na resposta.
13. Retorne somente o objeto definido pelo JSON Schema.
"""

# =========================================================
# ANALISAR COM GROQ
# =========================================================

analysis = groq(
    prompt
)


# =========================================================
# VALIDAR E NORMALIZAR REVIEW
# =========================================================

ALLOWED_KINDS = {
    "✨ Feature",
    "🐛 Correção",
    "📚 Documentação",
    "♻️ Refatoração",
    "🧪 Teste",
    "🔐 Segurança",
    "⚡ Performance",
    "🔧 Manutenção",
    "📝 Alteração",
}

ALLOWED_RISK = {"Baixo", "Médio", "Alto"}
ALLOWED_SEVERITY = {"Baixa", "Média", "Alta"}


def clamp_score(value):
    try:
        return max(0.0, min(10.0, float(value)))
    except (TypeError, ValueError):
        return None


def clamp_confidence(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def normalize_review(data):
    if not isinstance(data, dict):
        raise RuntimeError("A IA não retornou um objeto de review.")

    if data.get("categoria") not in ALLOWED_KINDS:
        data["categoria"] = "📝 Alteração"

    if data.get("risco") not in ALLOWED_RISK:
        data["risco"] = "Médio"

    for field in (
        "qualidade",
        "seguranca_nota",
        "manutenibilidade"
    ):
        score_value = clamp_score(data.get(field))

        if score_value is None:
            raise RuntimeError(
                f"Nota inválida ou ausente: {field}"
            )

        data[field] = score_value

    data["confianca_geral"] = clamp_confidence(
        data.get("confianca_geral")
    )

    problems = data.get("problemas_encontrados")

    if not isinstance(problems, list):
        problems = []

    normalized_problems = []

    for problem in problems[:20]:
        if not isinstance(problem, dict):
            continue

        severity = problem.get("severidade")

        if severity not in ALLOWED_SEVERITY:
            severity = "Baixa"

        confidence = clamp_confidence(
            problem.get("confianca")
        )

        normalized_problems.append({
            "severidade": severity,
            "problema": str(
                problem.get(
                    "problema",
                    "Problema não especificado."
                )
            ),
            "arquivo": str(
                problem.get("arquivo", "N/A")
            ),
            "linha": str(
                problem.get("linha", "N/A")
            ),
            "evidencia": str(
                problem.get(
                    "evidencia",
                    "Evidência não especificada."
                )
            ),
            "sugestao": str(
                problem.get(
                    "sugestao",
                    "Nenhuma sugestão específica."
                )
            ),
            "confianca": confidence
        })

    if not normalized_problems:
        normalized_problems = [{
            "severidade": "Baixa",
            "problema": "Nenhum problema evidente no diff.",
            "arquivo": "N/A",
            "linha": "N/A",
            "evidencia": (
                "O diff não apresentou evidência suficiente "
                "para registrar um problema."
            ),
            "sugestao": "Nenhuma ação corretiva necessária.",
            "confianca": data["confianca_geral"]
        }]

    data["problemas_encontrados"] = normalized_problems

    return data


# =========================================================
# PROCESSAR RESPOSTA DA IA
# =========================================================

analysis = normalize_review(
    groq(prompt)
)

kind = analysis["categoria"]

summary = str(
    analysis["resumo_executivo"]
)

what_changed = str(
    analysis["o_que_foi_alterado"]
)

how_it_works = str(
    analysis["como_funciona"]
)

impact = str(
    analysis["impacto"]
)

strengths = clean_list(
    analysis["pontos_fortes"]
)

compatibility = str(
    analysis["compatibilidade"]
)

regression = str(
    analysis["regressao"]
)

performance = str(
    analysis["performance"]
)

security = str(
    analysis["seguranca"]
)

tests = str(
    analysis["testes"]
)

improvements = str(
    analysis["melhorias"]
)

quality = analysis["qualidade"]
security_score = analysis["seguranca_nota"]
maintainability = analysis["manutenibilidade"]
risk = analysis["risco"]
confidence = analysis["confianca_geral"]

problems = analysis["problemas_encontrados"]

main_files = clean_list(
    analysis["arquivos_principais"]
)


# =========================================================
# BUSCAR PROJETO NO NOTION
# =========================================================



page_id = None

if NOTION_ENABLED:
    query = notion(
        "POST",
        f"data_sources/{DATA_SOURCE}/query",
        {
            "filter": {
                "property": "Repositorio",
                "url": {
                    "equals": REPO_URL
                }
            },
            "page_size": 1,
        },
    )

    page_id = (
        query["results"][0]["id"]
        if query.get("results")
        else None
    )


# =========================================================
# CRIAR CONTEÚDO DA DOCUMENTAÇÃO
# =========================================================



children = [
    {
        "object": "block",
        "type": "divider",
        "divider": {},
    },
    heading(2, f"📌 {kind}"),
    paragraph(MESSAGE.strip() or "(sem mensagem)"),
    paragraph(
        f"👤 Autor: {AUTHOR} | 📅 Data: {DATE}"
    ),
    paragraph(f"🔗 Commit: {SHA[:7]}"),
    heading(3, "🧠 Resumo executivo"),
    paragraph(summary),
    heading(3, "📌 O que foi alterado"),
    paragraph(what_changed),
    heading(3, "⚙️ Como funciona"),
    paragraph(how_it_works),
    heading(3, "📈 Impacto"),
    paragraph(impact),
    heading(3, "💪 Pontos fortes"),
    *[
        bullet(item)
        for item in strengths[:10]
    ],
    heading(3, "🔗 Compatibilidade"),
    paragraph(compatibility),
    heading(3, "♻️ Risco de regressão"),
    paragraph(regression),
    heading(3, "⚡ Performance"),
    paragraph(performance),
    heading(3, "🔐 Segurança"),
    paragraph(security),
    heading(3, "🧪 Testes"),
    paragraph(tests),
    heading(3, "💡 Melhorias sugeridas"),
    paragraph(improvements),
    heading(3, "🚨 Problemas encontrados"),
]

# =========================================================
# PROBLEMAS ENCONTRADOS
# =========================================================

for problem in problems[:20]:
    children.append(
        bullet(
            f"🚨 {problem['severidade']}: "
            f"{problem['problema']}"
        )
    )

    children.append(
        bullet(
            f"📁 {problem['arquivo']} | "
            f"📍 Linha: {problem['linha']} | "
            f"🔎 Evidência: {problem['evidencia']}"
        )
    )

    children.append(
        bullet(
            f"💡 Sugestão: {problem['sugestao']} | "
            f"🎯 Confiança: {problem['confianca'] * 100:.0f}%"
        )
    )

children.extend([
    heading(3, "📊 Avaliação automática"),
    bullet(f"⭐ Qualidade: {quality:.1f}/10"),
    bullet(f"🔐 Segurança: {security_score:.1f}/10"),
    bullet(f"🛠️ Manutenibilidade: {maintainability:.1f}/10"),
    bullet(f"⚠️ Risco: {risk}"),
    bullet(f"🎯 Confiança geral: {confidence * 100:.0f}%"),
    heading(3, "📁 Arquivos principais"),
])


# =========================================================
# ARQUIVOS PRINCIPAIS
# =========================================================



if main_files:

    for item in main_files[:20]:

        children.append(

            bullet(
                item
            )
        )


else:

    for status, path in files[:20]:

        label = {

            "A":
                "➕ Adicionado",

            "M":
                "✏️ Modificado",

            "D":
                "➖ Removido",

            "R":
                "🔄 Renomeado",

        }.get(

            status[:1],

            "📝 Alterado"
        )


        children.append(

            bullet(

                f"{label}: {path}"
            )
        )


# =========================================================
# RESUMO
# =========================================================

children.extend([

    heading(
        3,
        "📊 Resumo do commit"
    ),


    bullet(
        f"Arquivos alterados: "
        f"{len(files)}"
    ),


    bullet(
        f"Linhas adicionadas: "
        f"{added}"
    ),


    bullet(
        f"Linhas removidas: "
        f"{deleted}"
    ),


    paragraph(
        "🤖 Análise gerada automaticamente "
        "pelo GitHub Actions utilizando "
        "Groq e registrada no Notion."
    ),
])


# =========================================================
# SINCRONIZAR COM NOTION
# =========================================================

if NOTION_ENABLED:
    if not page_id:
        page = notion(
            "POST",
            "pages",
            {
                "parent": {
                    "data_source_id": DATA_SOURCE
                },
                "properties": {
                    "Projeto": {
                        "title": [
                            {
                                "text": {
                                    "content": PROJECT
                                }
                            }
                        ]
                    },
                    "Repositorio": {
                        "url": REPO_URL
                    },
                    "Status": {
                        "select": {
                            "name": "Ativo"
                        }
                    },
                    "Ultimo commit": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": SHA
                                }
                            }
                        ]
                    },
                    "Ultima atualizacao": {
                        "date": {
                            "start": DATE
                        }
                    },
                },
                "children": children[:100],
            },
        )

        print(
            f"✅ Projeto '{PROJECT}' criado no Notion."
        )
        print(page.get("url", ""))

    else:
        notion(
            "PATCH",
            f"pages/{page_id}",
            {
                "properties": {
                    "Ultimo commit": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": SHA
                                }
                            }
                        ]
                    },
                    "Ultima atualizacao": {
                        "date": {
                            "start": DATE
                        }
                    },
                }
            },
        )

        notion(
            "PATCH",
            f"blocks/{page_id}/children",
            {
                "children": children[:100]
            },
        )

        print(
            f"✅ Projeto '{PROJECT}' atualizado no Notion."
        )
else:
    print("ℹ️ Notion desativado — review mantido no GitHub Actions.")


# =========================================================
# RESUMO FINAL DO GITHUB ACTIONS
# =========================================================



print(
    f"📦 {len(files)} arquivos | "
    f"➕ {added} linhas | "
    f"➖ {deleted} linhas"
)


print(
    f"⭐ Qualidade: "
    f"{quality:.1f}/10"
    if quality is not None
    else "⭐ Qualidade: N/A"
)


print(
    f"🔐 Segurança: "
    f"{security_score:.1f}/10"
    if security_score is not None
    else "🔐 Segurança: N/A"
)


print(
    f"🛠️ Manutenibilidade: "
    f"{maintainability:.1f}/10"
    if maintainability is not None
    else "🛠️ Manutenibilidade: N/A"
)


print(
    f"⚠️ Risco: {risk}"
)


print(
    f"🔗 {COMMIT_URL}"
)


print(
    f"📦 {len(files)} arquivos | "
    f"➕ {added} linhas | "
    f"➖ {deleted} linhas"
)

print(f"⭐ Qualidade: {quality:.1f}/10")
print(f"🔐 Segurança: {security_score:.1f}/10")
print(f"🛠️ Manutenibilidade: {maintainability:.1f}/10")
print(f"⚠️ Risco: {risk}")
print(f"🎯 Confiança: {confidence * 100:.0f}%")
print(f"🔗 {COMMIT_URL}")


# =========================================================
# QUALITY GATE
# =========================================================

high_risk = risk == "Alto"
low_score = min(
    quality,
    security_score,
    maintainability
) < MIN_SCORE if MIN_SCORE > 0 else False

if high_risk and FAIL_ON_HIGH_RISK:
    print(
        "❌ QUALITY GATE: risco Alto detectado."
    )
    raise SystemExit(2)

if low_score:
    print(
        f"❌ QUALITY GATE: nota abaixo do mínimo "
        f"configurado ({MIN_SCORE:.1f})."
    )
    raise SystemExit(2)

print("✅ AI DevOps review concluído com sucesso.")

# Outputs para GitHub Actions
github_output = os.environ.get("GITHUB_OUTPUT")

if github_output:
    with open(
        github_output,
        "a",
        encoding="utf-8"
    ) as output_file:
        output_file.write(
            f"quality={quality:.1f}\n"
            f"security={security_score:.1f}\n"
            f"maintainability={maintainability:.1f}\n"
            f"risk={risk}\n"
            f"confidence={confidence:.2f}\n"
        )



# =========================================================
# GITHUB STEP SUMMARY
# =========================================================

summary_path = os.environ.get("GITHUB_STEP_SUMMARY")

if summary_path:
    summary_lines = [
        f"# 🤖 AI DevOps Review",
        "",
        f"**Projeto:** {PROJECT}",
        f"**Commit:** [{SHA[:7]}]({COMMIT_URL})",
        "",
        f"## 📊 Avaliação",
        f"- ⭐ Qualidade: **{quality:.1f}/10**",
        f"- 🔐 Segurança: **{security_score:.1f}/10**",
        f"- 🛠️ Manutenibilidade: **{maintainability:.1f}/10**",
        f"- ⚠️ Risco: **{risk}**",
        f"- 🎯 Confiança: **{confidence * 100:.0f}%**",
        "",
        "## 🧠 Resumo",
        summary,
        "",
        "## 🚨 Problemas"
    ]

    for problem in problems[:20]:
        summary_lines.append(
            f"- **{problem['severidade']}** — "
            f"{problem['problema']} "
            f"({problem['arquivo']}:{problem['linha']})"
        )

    with open(
        summary_path,
        "a",
        encoding="utf-8"
    ) as summary_file:
        summary_file.write(
            "\n".join(summary_lines) + "\n"
        )


# ============================================================
# Autor: João Pedro de Oliveira (github.com/jpDev05) - 2026
# ============================================================
