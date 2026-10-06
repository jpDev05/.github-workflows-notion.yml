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

TOKEN = os.environ["NOTION_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

VERSION = "2025-09-03"

DATA_SOURCE = "d4190e15-cd71-4d55-8706-1ccfeb0227fd"


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
# GROQ
# =========================================================

def groq(prompt):

    body = {

        "model": "openai/gpt-oss-20b",

        "messages": [

            {
                "role": "system",

                "content": (
                    "Você é um engenheiro de software "
                    "sênior, especialista em documentação, "
                    "code review, segurança e testes. "

                    "Analise SOMENTE o commit e o diff "
                    "fornecidos. "

                    "Nunca invente funcionalidades, arquivos, "
                    "vulnerabilidades, testes ou comportamentos "
                    "que não possam ser sustentados pelo diff. "

                    "Responda sempre em português do Brasil. "

                    "Se não houver evidência suficiente para "
                    "uma conclusão, diga explicitamente "
                    "que não foi possível determinar."
                ),
            },

            {
                "role": "user",

                "content": prompt,
            },
        ],

        "temperature": 0.2,

        "max_tokens": 1800,
    }

    data = json.dumps(
        body
    ).encode()

    req = urllib.request.Request(

        "https://api.groq.com/openai/v1/chat/completions",

        data=data,

        method="POST",

        headers={

            "Authorization":
                f"Bearer {GROQ_API_KEY}",

            "Content-Type":
                "application/json",

            # Importante para evitar problemas
            # com o User-Agent padrão do urllib.
            "User-Agent":
                "github-actions-groq-notion/1.0",
        },
    )


    # -----------------------------------------------------
    # Tentativas para erros temporários
    # -----------------------------------------------------

    max_attempts = 3


    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            print(
                "🤖 Enviando alteração "
                "para a Groq..."
            )

            with urllib.request.urlopen(
                req,
                timeout=60
            ) as response:

                result = json.loads(
                    response.read().decode()
                )


            content = (
                result
                ["choices"]
                [0]
                ["message"]
                ["content"]
                .strip()
            )


            if not content:

                raise RuntimeError(
                    "A Groq retornou uma "
                    "resposta vazia."
                )


            print(
                "✅ Análise gerada pela Groq."
            )


            # -------------------------------------------------
            # Remover cercas Markdown caso a IA coloque JSON
            # dentro de ```json ... ```
            # -------------------------------------------------

            if content.startswith(
                "```"
            ):

                content = content.replace(
                    "```json",
                    "",
                    1
                )

                content = content.replace(
                    "```",
                    "",
                    1
                ).strip()


            # -------------------------------------------------
            # Converter resposta para JSON
            # -------------------------------------------------

            try:

                return json.loads(
                    content
                )


            except json.JSONDecodeError:

                print(
                    "⚠️ A Groq não retornou "
                    "JSON válido."
                )

                print(
                    "⚠️ Usando resposta "
                    "como documentação."
                )


                return {

                    "categoria":
                        "📝 Alteração",

                    "o_que_foi_alterado":
                        content,

                    "como_funciona":
                        "Não foi possível "
                        "estruturar esta seção.",

                    "impacto":
                        "Não foi possível "
                        "determinar automaticamente.",

                    "seguranca":
                        "Não foi possível "
                        "realizar uma análise "
                        "estruturada de segurança.",

                    "testes":
                        "Revisar e executar "
                        "os testes existentes "
                        "relacionados à alteração.",

                    "melhorias":
                        "Não foi possível gerar "
                        "sugestões estruturadas.",

                    "qualidade":
                        0,

                    "seguranca_nota":
                        0,

                    "manutenibilidade":
                        0,

                    "risco":
                        "Não determinado",

                    "arquivos_principais":
                        [],
                }


        except urllib.error.HTTPError as error:

            details = error.read().decode(
                errors="replace"
            )


            # -------------------------------------------------
            # Erros temporários
            # -------------------------------------------------

            if error.code in (
                429,
                500,
                502,
                503,
                504
            ) and attempt < max_attempts:

                print(
                    f"⚠️ Groq retornou "
                    f"{error.code}."
                )

                print(
                    "⏳ Tentando novamente..."
                )

                time.sleep(
                    attempt * 3
                )

                continue


            raise RuntimeError(
                f"Groq API {error.code}: "
                f"{details}"
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

MAX_DIFF = 30000


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
# PROMPT DA IA
# =========================================================

prompt = f"""

Analise o commit abaixo como um
code reviewer e documentador técnico.

Projeto:
{PROJECT}

Repositório:
{REPO}

Commit:
{SHA}

Autor:
{AUTHOR}

Data:
{DATE}


Mensagem do commit:
{MESSAGE}


ESTATÍSTICAS:

Arquivos alterados:
{len(files)}

Linhas adicionadas:
{added}

Linhas removidas:
{deleted}


ARQUIVOS:

{chr(10).join(
    f"- {status}: {path}"
    for status, path in files[:70]
)}


DIFF:

{diff}


==================================================
OBJETIVO
==================================================

Analise a alteração tecnicamente.

A resposta DEVE ser um JSON válido.

Não utilize Markdown.

Não escreva nenhuma explicação
fora do JSON.


==================================================
ESTRUTURA OBRIGATÓRIA
==================================================

{{
    "categoria":
        "✨ Feature",

    "o_que_foi_alterado":
        "explicação objetiva da alteração",

    "como_funciona":
        "explicação técnica do funcionamento",

    "impacto":
        "impactos técnicos relevantes",

    "seguranca":
        "análise de segurança baseada somente no diff",

    "testes":
        "testes recomendados ou que possam ser inferidos",

    "melhorias":
        "sugestões de melhoria",

    "problemas_encontrados":
        [
            {{
                "severidade": "Baixa",
                "problema": "descrição objetiva ou nenhum problema evidente",
                "arquivo": "arquivo relacionado ou N/A",
                "sugestao": "ação recomendada ou N/A"
            }}
        ],

    "qualidade":
        8.0,

    "seguranca_nota":
        8.0,

    "manutenibilidade":
        8.0,

    "risco":
        "Baixo",

    "arquivos_principais":
        [
            "arquivo: papel na alteração"
        ]
}}


==================================================
CATEGORIAS PERMITIDAS
==================================================

✨ Feature

🐛 Correção

📚 Documentação

♻️ Refatoração

🧪 Teste

🔐 Segurança

⚡ Performance

🔧 Manutenção

📝 Alteração


==================================================
REGRAS
==================================================

1. Não invente funcionalidades.

2. Não invente vulnerabilidades.

3. Não invente testes executados.

4. Não diga que algo é seguro apenas
   porque não encontrou problemas.

5. Para segurança, diferencie:

   "Nenhum problema evidente no diff"

   de:

   "Segurança garantida".

6. Se não houver informação suficiente,
   informe isso.

7. As notas são OBRIGATÓRIAS e devem ser números JSON entre 0 e 10.
   Nunca use strings como "8/10"; use apenas 8 ou 8.5.

8. Dê notas coerentes com o diff:
   - qualidade: clareza e qualidade da implementação;
   - seguranca_nota: segurança observável na alteração;
   - manutenibilidade: facilidade de manter a alteração.
   Não use 0 apenas porque a nota não foi informada.

9. "problemas_encontrados" é OBRIGATÓRIO.
   Se não houver problema evidente, retorne uma lista com um item
   dizendo "Nenhum problema evidente no diff", sem inventar problemas.

10. Cada problema deve ter:
   severidade, problema, arquivo e sugestao.

11. O risco deve ser:

   Baixo

   Médio

   Alto

9. Seja técnico e objetivo.

10. Não inclua o diff inteiro na resposta.

"""


# =========================================================
# ANALISAR COM GROQ
# =========================================================

analysis = groq(
    prompt
)


# =========================================================
# PROCESSAR RESPOSTA DA IA
# =========================================================

if not isinstance(
    analysis,
    dict
):

    analysis = {}


allowed_kinds = {

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


ai_kind = str(

    analysis.get(
        "categoria",
        ""
    )

).strip()


if ai_kind in allowed_kinds:

    kind = ai_kind


# =========================================================
# RESULTADOS DA IA
# =========================================================

what_changed = str(

    analysis.get(

        "o_que_foi_alterado",

        "Não foi possível "
        "gerar o resumo."
    )
)


how_it_works = str(

    analysis.get(

        "como_funciona",

        "Não foi possível "
        "determinar o funcionamento."
    )
)


impact = str(

    analysis.get(

        "impacto",

        "Não foi possível "
        "determinar o impacto."
    )
)


security = str(

    analysis.get(

        "seguranca",

        "Não foi possível "
        "realizar a análise."
    )
)


tests = str(

    analysis.get(

        "testes",

        "Não foram identificados "
        "testes específicos."
    )
)


improvements = str(

    analysis.get(

        "melhorias",

        "Nenhuma melhoria específica "
        "foi identificada."
    )
)


risk = str(

    analysis.get(

        "risco",

        "Não determinado"
    )
)


main_files = clean_list(

    analysis.get(

        "arquivos_principais",

        []
    )
)

problems = analysis.get(
    "problemas_encontrados",
    []
)

if not isinstance(problems, list):
    problems = []

# Garante que sempre exista uma seção de problemas.
if not problems:
    problems = [
        {
            "severidade": "Baixa",
            "problema": "Nenhum problema evidente no diff.",
            "arquivo": "N/A",
            "sugestao": "Nenhuma ação corretiva identificada."
        }
    ]

quality = score(
    analysis.get("qualidade"),
    fallback=None
)

security_score = score(
    analysis.get("seguranca_nota"),
    fallback=None
)

maintainability = score(
    analysis.get("manutenibilidade"),
    fallback=None
)


# =========================================================
# BUSCAR PROJETO NO NOTION
# =========================================================

query = notion(

    "POST",

    f"data_sources/{DATA_SOURCE}/query",

    {

        "filter": {

            "property":
                "Repositorio",

            "url": {

                "equals":
                    REPO_URL
            }
        },

        "page_size":
            1,
    },
)


page_id = (

    query["results"][0]["id"]

    if query.get(
        "results"
    )

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


    heading(
        2,
        f"📌 {kind}"
    ),


    paragraph(
        MESSAGE.strip()
        or "(sem mensagem)"
    ),


    paragraph(
        f"👤 Autor: {AUTHOR}"
        f" | 📅 Data: {DATE}"
    ),


    paragraph(
        f"🔗 Commit: {SHA[:7]}"
    ),


    heading(
        3,
        "🤖 Análise e documentação da IA"
    ),


    heading(
        3,
        "📌 O que foi alterado"
    ),

    paragraph(
        what_changed
    ),


    heading(
        3,
        "⚙️ Como funciona"
    ),

    paragraph(
        how_it_works
    ),


    heading(
        3,
        "📈 Impacto"
    ),

    paragraph(
        impact
    ),


    heading(
        3,
        "🔐 Segurança"
    ),

    paragraph(
        security
    ),


    heading(
        3,
        "🧪 Testes recomendados"
    ),

    paragraph(
        tests
    ),


    heading(
        3,
        "💡 Melhorias sugeridas"
    ),

    paragraph(
        improvements
    ),


    heading(
        3,
        "🚨 Problemas encontrados"
    ),
]


# =========================================================
# PROBLEMAS ENCONTRADOS
# =========================================================

for problem in problems[:20]:

    if isinstance(problem, dict):

        severity = str(
            problem.get(
                "severidade",
                "Não determinada"
            )
        )

        problem_text = str(
            problem.get(
                "problema",
                "Problema não especificado."
            )
        )

        file_name = str(
            problem.get(
                "arquivo",
                "N/A"
            )
        )

        suggestion = str(
            problem.get(
                "sugestao",
                "N/A"
            )
        )

        children.append(
            bullet(
                f"🚨 {severity}: {problem_text}"
            )
        )

        children.append(
            bullet(
                f"📁 Arquivo: {file_name} | 💡 Sugestão: {suggestion}"
            )
        )

    else:

        children.append(
            bullet(
                str(problem)
            )
        )


children.extend([

    heading(
        3,
        "📊 Avaliação automática"
    ),

    bullet(
        f"⭐ Qualidade: "
        f"{quality:.1f}/10"
        if quality is not None
        else "⭐ Qualidade: N/A"
    ),

    bullet(
        f"🔐 Segurança: "
        f"{security_score:.1f}/10"
        if security_score is not None
        else "🔐 Segurança: N/A"
    ),

    bullet(
        f"🛠️ Manutenibilidade: "
        f"{maintainability:.1f}/10"
        if maintainability is not None
        else "🛠️ Manutenibilidade: N/A"
    ),

    bullet(
        f"⚠️ Risco: "
        f"{risk}"
    ),

    heading(
        3,
        "📁 Arquivos principais"
    ),
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
# CRIAR PROJETO NO NOTION
# =========================================================

if not page_id:

    page = notion(

        "POST",

        "pages",

        {

            "parent": {

                "data_source_id":
                    DATA_SOURCE
            },


            "properties": {

                "Projeto": {

                    "title": [

                        {

                            "text": {

                                "content":
                                    PROJECT
                            }
                        }
                    ]
                },


                "Repositorio": {

                    "url":
                        REPO_URL
                },


                "Status": {

                    "select": {

                        "name":
                            "Ativo"
                    }
                },


                "Ultimo commit": {

                    "rich_text": [

                        {

                            "text": {

                                "content":
                                    SHA
                            }
                        }
                    ]
                },


                "Ultima atualizacao": {

                    "date": {

                        "start":
                            DATE
                    }
                },
            },


            "children":
                children[:100],
        },
    )


    print(
        f"✅ Projeto '{PROJECT}' "
        "criado no Notion."
    )


    print(
        page.get(
            "url",
            ""
        )
    )


# =========================================================
# ATUALIZAR PROJETO EXISTENTE
# =========================================================

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

                                "content":
                                    SHA
                            }
                        }
                    ]
                },


                "Ultima atualizacao": {

                    "date": {

                        "start":
                            DATE
                    }
                },
            }
        },
    )


    notion(

        "PATCH",

        f"blocks/{page_id}/children",

        {

            "children":
                children[:100]
        },
    )


    print(
        f"✅ Projeto '{PROJECT}' "
        "atualizado no Notion."
    )


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


# ============================================================
# Autor: João Pedro de Oliveira (github.com/jpDev05) - 2026
# ============================================================