"""Hook PreToolUse (Bash y PowerShell): frena que contado/ o una credencial lleguen a git.

contado/ usa la key del gateway de Felipe y la clave del robot de Google: no se sube a
GitHub (regla de Tobias del 21-oct-2026). .git/info/exclude ya lo saca de `git add .`,
pero no de un `git add -f` ni de algo que ya este en el indice; este hook es la segunda
barrera, y vale tambien para las corridas desatendidas (claude -p lee este settings).

Bloquea (exit 2, el motivo va a Claude por stderr):
- un comando de git que nombre una ruta sensible (add, commit, mv, stash, etc.);
- `git add` forzado (-f / --force) de todo el arbol;
- `git commit` con algo sensible ya en el indice (o en el arbol, si es commit -a);
- `git push` con algo sensible en los commits que todavia no estan en el remoto.
Cualquier otro comando sale con 0 sin hacer nada.
"""
import json
import re
import subprocess
import sys

# .env sola o con sufijo (.env.local), pero no .env.example, que es la plantilla publica.
SENSIBLE = re.compile(r"(^|[\\/\s\"'])(contado([\\/]|$|[\s\"'])|\.env(?!\.example)(\.[\w-]+)?($|[\s\"'])"
                      r"|cuenta_servicio[\w-]*\.json)")
GIT = re.compile(r"\bgit(\.exe)?\s+(?:-[Cc]\s+\S+\s+)*(add|commit|push|mv|stash|update-index|rm)\b")
# El mensaje del commit no cuenta: "tablero de contado" no es una ruta. Se sacan los -m
# (comillas, here-string de PowerShell) y los heredoc de bash antes de buscar rutas.
MENSAJE = re.compile(r"(-m|--message)(=|\s+)(@'.*?'@|@\".*?\"@|\"(?:[^\"\\]|\\.)*\"|'[^']*'|\S+)", re.S)
HEREDOC = re.compile(r"<<-?\s*['\"]?(\w+)['\"]?.*?^\s*\1\s*$", re.S | re.M)


def sensibles(rutas):
    return [r for r in rutas if SENSIBLE.search(" " + r.strip() + " ")]


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [x for x in r.stdout.splitlines() if x.strip()] if r.returncode == 0 else []


def bloquear(motivo):
    print(f"Bloqueado por .claude/hooks/proteger_git.py: {motivo} contado/, .env y cuenta_servicio.json "
          "no se suben a GitHub (regla de Tobias). Stagea por ruta y dejalos afuera.", file=sys.stderr)
    sys.exit(2)


def main():
    try:
        datos = json.load(sys.stdin)
    except ValueError:
        return
    comando = (datos.get("tool_input") or {}).get("command") or ""
    subcomandos = {m.group(2) for m in GIT.finditer(comando)}
    if not subcomandos:
        return
    if subcomandos - {"push"} and sensibles([MENSAJE.sub(" ", HEREDOC.sub(" ", comando))]):
        bloquear("el comando de git nombra una ruta sensible.")
    if "add" in subcomandos and re.search(r"\s(-f|--force)\b", comando) and re.search(r"\s(\.|-A|--all)(\s|$)", comando):
        bloquear("`git add` forzado de todo el arbol se saltea .git/info/exclude.")
    if "commit" in subcomandos:
        rutas = git("diff", "--cached", "--name-only")
        if re.search(r"\scommit\b[^;&|]*\s(-a|--all|-\w*a\w*)\b", comando):
            rutas += git("diff", "--name-only")
        malas = sensibles(rutas)
        if malas:
            bloquear(f"hay archivos sensibles en el commit ({', '.join(malas[:5])}).")
    if "push" in subcomandos:
        malas = sensibles(git("log", "@{u}..HEAD", "--name-only", "--format="))
        if malas:
            bloquear(f"hay commits sin subir que tocan archivos sensibles ({', '.join(sorted(set(malas))[:5])}).")


if __name__ == "__main__":
    main()
