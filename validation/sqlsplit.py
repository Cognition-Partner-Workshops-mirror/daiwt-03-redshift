"""Split a SQL script into statements.

Splits on ';' outside of string literals, quoted identifiers, comments,
dollar-quoted bodies ($$...$$ / $tag$...$tag$) and BEGIN...END / CASE...END
blocks, so Redshift procedures and Databricks SQL scripting blocks stay whole.
"""
import re

_wordRe = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_dollarRe = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")
_nonCountedEnds = {"IF", "LOOP", "WHILE", "FOR", "REPEAT"}
_txnBeginFollowers = {"TRANSACTION", "WORK"}


def _nextWord(sql, pos):
    m = re.compile(r"\s*([A-Za-z_]+|;)").match(sql, pos)
    return m.group(1).upper() if m else ""


def splitStatements(sql):
    statements = []
    buf = []
    depth = 0
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if ch == "-" and nxt == "-":
            end = sql.find("\n", i)
            end = n if end == -1 else end
            buf.append(sql[i:end])
            i = end
            continue
        if ch == "/" and nxt == "*":
            end = sql.find("*/", i + 2)
            end = n if end == -1 else end + 2
            buf.append(sql[i:end])
            i = end
            continue
        if ch in ("'", '"', "`"):
            j = i + 1
            while j < n:
                if sql[j] == ch:
                    if j + 1 < n and sql[j + 1] == ch:
                        j += 2
                        continue
                    break
                if sql[j] == "\\" and ch == "'":
                    j += 2
                    continue
                j += 1
            buf.append(sql[i : j + 1])
            i = j + 1
            continue
        if ch == "$":
            m = _dollarRe.match(sql, i)
            if m:
                tag = m.group(0)
                end = sql.find(tag, m.end())
                end = n if end == -1 else end + len(tag)
                buf.append(sql[i:end])
                i = end
                continue
        if ch.isalpha() or ch == "_":
            m = _wordRe.match(sql, i)
            word = m.group(0).upper()
            prevIsIdentChar = i > 0 and (sql[i - 1].isalnum() or sql[i - 1] in "_.")
            if not prevIsIdentChar:
                if word == "BEGIN":
                    if _nextWord(sql, m.end()) not in _txnBeginFollowers | {";", ""}:
                        depth += 1
                elif word == "CASE":
                    depth += 1
                elif word == "END" and depth > 0 and _nextWord(sql, m.end()) not in _nonCountedEnds:
                    depth -= 1
            buf.append(m.group(0))
            i = m.end()
            continue
        if ch == ";" and depth == 0:
            stmt = "".join(buf).strip()
            if _hasCode(stmt):
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    stmt = "".join(buf).strip()
    if _hasCode(stmt):
        statements.append(stmt)
    return statements


def _hasCode(stmt):
    stripped = re.sub(r"--[^\n]*|/\*.*?\*/", "", stmt, flags=re.DOTALL)
    return bool(stripped.strip())
