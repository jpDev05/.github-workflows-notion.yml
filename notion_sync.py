import json, os, subprocess, urllib.request, urllib.error

TOKEN = os.environ["NOTION_TOKEN"]
VERSION = "2025-09-03"
DATA_SOURCE = "d4190e15-cd71-4d55-8706-1ccfeb0227fd"
SHA = os.environ["COMMIT_SHA"]
BEFORE = os.environ["BEFORE_SHA"]
MESSAGE = os.environ.get("COMMIT_MESSAGE", "")
AUTHOR = os.environ.get("COMMIT_AUTHOR", "Desconhecido")
DATE = os.environ.get("COMMIT_DATE", "")
REPO = os.environ["REPOSITORY"]
REPO_URL = os.environ["REPOSITORY_URL"]
COMMIT_URL = os.environ["COMMIT_URL"]
PROJECT = REPO.split("/", 1)[1]


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def notion(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Notion-Version": VERSION,
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Notion API {error.code}: {error.read().decode(errors='replace')}")


def block(kind, content):
    return {
        "object": "block",
        "type": kind,
        kind: {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]},
    }


def bullet(content):
    return block("bulleted_list_item", content)


def heading(level, content):
    return block(f"heading_{level}", content)


zero = "0" * 40
if BEFORE != zero:
    try:
        git("cat-file", "-e", f"{BEFORE}^{{commit}}")
        base = BEFORE
    except subprocess.CalledProcessError:
        base = git("rev-parse", f"{SHA}^")
else:
    base = git("hash-object", "-t", "tree", "/dev/null")

raw_files = git("diff", "--name-status", base, SHA)
files = [line.split("\t", 1) for line in raw_files.splitlines() if "\t" in line]
raw_stats = git("diff", "--numstat", base, SHA)
added = deleted = 0
for line in raw_stats.splitlines():
    parts = line.split("\t")
    if len(parts) >= 2:
        try:
            added += int(parts[0])
            deleted += int(parts[1])
        except ValueError:
            pass

query = notion("POST", f"data_sources/{DATA_SOURCE}/query", {
    "filter": {"property": "Repositorio", "url": {"equals": REPO_URL}},
    "page_size": 1,
})
page_id = query["results"][0]["id"] if query.get("results") else None

kind = "📝 Alteração"
for prefix, label in [
    ("feat:", "✨ Feature"),
    ("fix:", "🐛 Correção"),
    ("docs:", "📚 Documentação"),
    ("refactor:", "♻️ Refatoração"),
    ("test:", "🧪 Teste"),
    ("chore:", "🔧 Manutenção"),
]:
    if MESSAGE.strip().lower().startswith(prefix):
        kind = label
        break

children = [
    {"object": "block", "type": "divider", "divider": {}},
    heading(2, f"📌 {kind}"),
    block("paragraph", MESSAGE.strip() or "(sem mensagem)"),
    block("paragraph", f"👤 Autor: {AUTHOR} | 📅 Data: {DATE}"),
    block("paragraph", f"🔗 Commit: {SHA[:7]}"),
    heading(3, "📊 Resumo da alteração"),
    bullet(f"Arquivos alterados: {len(files)}"),
    bullet(f"Linhas adicionadas: {added}"),
    bullet(f"Linhas removidas: {deleted}"),
    heading(3, "📁 Arquivos alterados"),
]

for status, path in files[:70]:
    label = {"A": "➕ Adicionado", "M": "✏️ Modificado", "D": "➖ Removido"}.get(status[:1], "📝 Alterado")
    children.append(bullet(f"{label}: {path}"))

children.append(block("paragraph", "ℹ️ Documentação gerada automaticamente pelo GitHub Actions, sem API de IA paga."))

if not page_id:
    page = notion("POST", "pages", {
        "parent": {"data_source_id": DATA_SOURCE},
        "properties": {
            "Projeto": {"title": [{"text": {"content": PROJECT}}]},
            "Repositorio": {"url": REPO_URL},
            "Status": {"select": {"name": "Ativo"}},
            "Ultimo commit": {"rich_text": [{"text": {"content": SHA}}]},
            "Ultima atualizacao": {"date": {"start": DATE}},
        },
        "children": children[:100],
    })
    print(f"✅ Projeto '{PROJECT}' criado no Notion.")
    print(page.get("url", ""))
else:
    notion("PATCH", f"pages/{page_id}", {
        "properties": {
            "Ultimo commit": {"rich_text": [{"text": {"content": SHA}}]},
            "Ultima atualizacao": {"date": {"start": DATE}},
        }
    })
    notion("PATCH", f"blocks/{page_id}/children", {"children": children[:100]})
    print(f"✅ Projeto '{PROJECT}' atualizado no Notion.")

print(f"📦 {len(files)} arquivos | ➕ {added} linhas | ➖ {deleted} linhas")
print(f"🔗 {COMMIT_URL}")
