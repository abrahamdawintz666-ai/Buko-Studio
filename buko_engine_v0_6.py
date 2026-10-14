#!/usr/bin/env python3
"""BuKo engine prototype v0.6.

Adds decimal literals, boolean literals and EN saisir with injectable input.
Includes functions, conditional loops, scoped variables, and execution guards.
Still an experimental interpreter, not a native compiler.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Token:
    kind: str
    value: object
    line: int
    column: int


class BuKoError(Exception):
    def __init__(self, message, token, category="Erreur"):
        super().__init__(message)
        self.message = message
        self.token = token
        self.category = category

    def formatted(self, filename):
        return (f"{filename}:{self.token.line}:{self.token.column}: "
                f"{self.category}\n  {self.message}")


class Lexer:
    def __init__(self, source):
        self.source = source
        self.i = 0
        self.line = 1
        self.col = 1
        self.tokens = []

    def peek(self):
        return self.source[self.i] if self.i < len(self.source) else ""

    def advance(self):
        ch = self.peek()
        if ch:
            self.i += 1
            if ch == "\n":
                self.line += 1
                self.col = 1
            else:
                self.col += 1
        return ch

    def tokenize(self):
        while self.peek():
            ch = self.peek()
            if ch.isspace():
                self.advance()
                continue
            line, col = self.line, self.col

            if ch == "#":
                while self.peek() and self.peek() != "\n":
                    self.advance()
                continue

            if ch == '"':
                self.advance()
                chars = []
                while self.peek() and self.peek() != '"':
                    if self.peek() == "\n":
                        raise BuKoError("Le texte doit se terminer avant la fin de la ligne.",
                                        Token("TEXT", "", line, col), "Erreur de texte")
                    if self.peek() == "\\":
                        self.advance()
                        esc = self.peek()
                        if not esc:
                            break
                        chars.append({"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(esc, esc))
                        self.advance()
                    else:
                        chars.append(self.advance())
                if self.peek() != '"':
                    raise BuKoError("Guillemet fermant manquant.",
                                    Token("TEXT", "", line, col), "Erreur de texte")
                self.advance()
                self.tokens.append(Token("TEXT", "".join(chars), line, col))
                continue

            if ch.isdigit():
                digits = []
                while self.peek().isdigit():
                    digits.append(self.advance())
                is_decimal = False
                if self.peek() == "." and self.i + 1 < len(self.source) and self.source[self.i + 1].isdigit():
                    is_decimal = True
                    digits.append(self.advance())
                    while self.peek().isdigit():
                        digits.append(self.advance())
                if self.peek() != "'":
                    raise BuKoError("Un nombre doit finir par une apostrophe, par exemple 18' ou 3.14'.",
                                    Token("NUMBER", "".join(digits), line, col), "Erreur de nombre")
                self.advance()
                raw = "".join(digits)
                self.tokens.append(Token("NUMBER", float(raw) if is_decimal else int(raw), line, col))
                continue

            if ch.isalpha() or ch == "_":
                chars = []
                while self.peek() and (self.peek().isalnum() or self.peek() == "_"):
                    chars.append(self.advance())
                self.tokens.append(Token("WORD", "".join(chars), line, col))
                continue

            # Multi-character ASCII comparison aliases.
            pair = self.source[self.i:self.i + 2]
            pair_symbols = {"!=": "NE", ">=": "GE", "<=": "LE"}
            if pair in pair_symbols:
                self.advance()
                self.advance()
                self.tokens.append(Token(pair_symbols[pair], pair, line, col))
                continue

            symbols = {
                "=": "EQUALS", "≠": "NE", ">": "GT", "<": "LT",
                "≥": "GE", "≤": "LE", "+": "PLUS", "−": "MINUS",
                "×": "MULTIPLY", "÷": "DIVIDE", ".": "END",
                "{": "LBRACE", "}": "RBRACE", "(": "LPAREN", ")": "RPAREN", ",": "COMMA"
            }
            if ch in symbols:
                self.advance()
                self.tokens.append(Token(symbols[ch], ch, line, col))
                continue

            if ch == "-":
                raise BuKoError("Utilise le signe mathématique − pour la soustraction.",
                                Token("UNKNOWN", ch, line, col), "Symbole non reconnu")
            raise BuKoError(f"Caractère non reconnu : {ch!r}.",
                            Token("UNKNOWN", ch, line, col), "Symbole non reconnu")

        self.tokens.append(Token("EOF", None, self.line, self.col))
        return self.tokens


@dataclass
class Expr:
    kind: str
    value: object
    token: Token
    left: object = None
    right: object = None
    args: object = None


@dataclass
class Statement:
    kind: str
    token: Token
    name: str = None
    declared_type: str = None
    expression: object = None
    condition_left: object = None
    condition_right: object = None
    condition_operator: str = "EQUALS"
    condition_terms: object = None
    condition_joiners: object = None
    body: object = None
    loop_count: object = None
    params: object = None


class Parser:
    precedence = {"PLUS": 10, "MINUS": 10, "MULTIPLY": 20, "DIVIDE": 20}

    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def cur(self):
        return self.tokens[self.i]

    def take(self):
        token = self.cur()
        if token.kind != "EOF":
            self.i += 1
        return token

    def error(self, message, token=None, category="Erreur de syntaxe"):
        raise BuKoError(message, token or self.cur(), category)

    def expect(self, kind, message):
        if self.cur().kind != kind:
            self.error(message)
        return self.take()

    def parse(self):
        result = []
        while self.cur().kind != "EOF":
            result.append(self.statement())
        return result

    def block(self):
        self.expect("LBRACE", "Une accolade ouvrante { est attendue pour commencer le bloc.")
        statements = []
        while self.cur().kind not in ("RBRACE", "EOF"):
            statements.append(self.statement())
        self.expect("RBRACE", "Accolade fermante } manquante pour terminer le bloc.")
        return statements

    def statement(self):
        first = self.cur()
        if first.kind == "WORD" and first.value not in ("AF", "CO", "BO", "FO", "nombre", "texte") and self.tokens[self.i + 1].kind == "EQUALS":
            name = self.take()
            self.take()  # =
            expr = self.expression()
            self.expect("END", "Un point (.) est attendu à la fin de l'affectation.")
            return Statement("assign", first, name=name.value, expression=expr)

        if first.kind == "WORD" and first.value in ("nombre", "texte", "booleen"):
            declared_type = self.take().value
            name = self.expect("WORD", "Nom de variable attendu après le type.")
            self.expect("EQUALS", "Le signe = est attendu après le nom de variable.")
            expr = self.expression()
            self.expect("END", "Un point (.) est attendu à la fin de l'instruction.")
            return Statement("declare", first, name.value, declared_type, expr)

        if first.kind == "WORD" and first.value == "AF":
            self.take()
            keyword = self.expect("WORD", "Le mot-clé « afficher » est attendu après AF.")
            if keyword.value != "afficher":
                self.error("Après AF, utilise le mot-clé « afficher ».", keyword)
            expr = self.expression()
            self.expect("END", "Un point (.) est attendu à la fin de l'instruction.")
            return Statement("display", first, expression=expr)

        if first.kind == "WORD" and first.value == "CO":
            self.take()
            si = self.expect("WORD", "Après CO, écris « si ».")
            if si.value != "si":
                self.error("Après CO, écris « si ».", si)

            # CO accepts comparisons joined with et/ou. A shorthand list such as
            # H = 18' ou 20' ou 22' compares H with each listed value.
            terms = []
            joiners = []
            left = self.expression()
            op = self.comparison_operator()
            right = self.expression()
            terms.append((left, op, right))
            anchor_left, anchor_op = left, op

            while self.cur().kind == "WORD" and self.cur().value in ("et", "ou"):
                joiner = self.take().value
                candidate = self.expression()
                if self.cur().kind in ("EQUALS", "NE", "GT", "LT", "GE", "LE"):
                    next_op = self.take().kind
                    next_right = self.expression()
                    terms.append((candidate, next_op, next_right))
                elif joiner == "ou" and anchor_op == "EQUALS":
                    # `CO si H = 18' ou 20'` is shorthand for H = 18' or H = 20'.
                    terms.append((anchor_left, anchor_op, candidate))
                else:
                    self.error(
                        "Après « et », ou après « ou » sans égalité abrégée, "
                        "écris une comparaison complète (ex. H ≥ 18').",
                        self.tokens[self.i - 1]
                    )
                joiners.append(joiner)

            body_start = self.cur()
            if body_start.kind == "LBRACE":
                body = self.block()
            elif body_start.kind == "WORD" and body_start.value == "AF":
                body = [self.statement()]
            else:
                self.error(
                    "Après la condition, écris directement AF afficher ... ou ouvre un bloc avec { ... }.",
                    body_start, "Erreur de syntaxe"
                )
            return Statement("condition", first, condition_left=left,
                             condition_right=right, condition_operator=op,
                             condition_terms=terms, condition_joiners=joiners, body=body)

        if first.kind == "WORD" and first.value == "BO":
            self.take()
            mode = self.expect("WORD", "Après BO, écris « répéter ».")
            if mode.value == "répéter":
                count = self.expression()
                body_start = self.cur()
                if body_start.kind != "LBRACE":
                    self.error("Après le nombre de répétitions, ouvre un bloc avec { ... }.",
                               body_start)
                body = self.block()
                return Statement("loop", first, loop_count=count, body=body)
            if mode.value == "tant_que":
                terms = []
                joiners = []
                left = self.expression()
                op = self.comparison_operator()
                right = self.expression()
                terms.append((left, op, right))
                while self.cur().kind == "WORD" and self.cur().value in ("et", "ou"):
                    joiner = self.take().value
                    left2 = self.expression()
                    op2 = self.comparison_operator()
                    right2 = self.expression()
                    terms.append((left2, op2, right2))
                    joiners.append(joiner)
                body = self.block()
                return Statement("while", first, condition_terms=terms,
                                 condition_joiners=joiners, body=body)
            self.error("Après BO, utilise « répéter » ou « tant_que ».", mode,
                       "Fonctionnalité non disponible")

        if first.kind == "WORD" and first.value == "EN":
            self.take()
            keyword = self.expect("WORD", "Après EN, écris « saisir ».")
            if keyword.value != "saisir":
                self.error("Après EN, écris « saisir ».", keyword)
            name = self.expect("WORD", "Nom de variable attendu après EN saisir.")
            prompt = self.expression() if self.cur().kind != "END" else None
            if prompt is not None and prompt.kind != "TEXT":
                self.error("Le message de saisie doit être un texte entre guillemets.", prompt.token)
            self.expect("END", "Un point (.) est attendu à la fin de la saisie.")
            return Statement("input", first, name=name.value, expression=prompt)

        if first.kind == "WORD" and first.value == "FO":
            self.take()
            name = self.expect("WORD", "Nom de fonction attendu après FO.")
            self.expect("LPAREN", "Une parenthèse ( est attendue après le nom de fonction.")
            params = []
            if self.cur().kind != "RPAREN":
                while True:
                    param = self.expect("WORD", "Nom de paramètre attendu.")
                    if param.value in ("AF", "CO", "BO", "FO", "RE", "nombre", "texte"):
                        self.error("Ce mot est réservé et ne peut pas être un paramètre.", param)
                    if param.value in params:
                        self.error(f"Paramètre dupliqué : « {param.value} ».", param)
                    params.append(param.value)
                    if self.cur().kind != "COMMA":
                        break
                    self.take()
            self.expect("RPAREN", "Parenthèse fermante ) attendue après les paramètres.")
            body = self.block()
            return Statement("function", first, name=name.value, params=params, body=body)

        if first.kind == "WORD" and first.value == "RE":
            self.take()
            keyword = self.expect("WORD", "Après RE, écris « retourner ».")
            if keyword.value != "retourner":
                self.error("Après RE, écris « retourner ».", keyword)
            expr = self.expression()
            self.expect("END", "Un point (.) est attendu après la valeur retournée.")
            return Statement("return", first, expression=expr)

        self.error("Instruction inconnue. Utilise « nombre », « texte » ou « AF afficher ».",
                   first)

    def comparison_operator(self):
        if self.cur().kind not in ("EQUALS", "NE", "GT", "LT", "GE", "LE"):
            self.error(
                "Opérateur de comparaison attendu : =, ≠, >, <, ≥ ou ≤.",
                self.cur(), "Erreur de condition"
            )
        return self.take().kind

    def expression(self, min_prec=0):
        token = self.take()
        if token.kind == "MINUS":
            right = self.expression(30)
            return Expr("UNARY_MINUS", "MINUS", token, right=right)
        if token.kind in ("NUMBER", "TEXT"):
            left = Expr(token.kind, token.value, token)
        elif token.kind == "WORD":
            if token.value in ("vrai", "faux"):
                left = Expr("BOOLEAN", token.value == "vrai", token)
            elif self.cur().kind == "LPAREN":
                self.take()
                args = []
                if self.cur().kind != "RPAREN":
                    while True:
                        args.append(self.expression())
                        if self.cur().kind != "COMMA":
                            break
                        self.take()
                self.expect("RPAREN", "Parenthèse fermante ) manquante après les arguments.")
                left = Expr("CALL", token.value, token, args=args)
            else:
                left = Expr("VARIABLE", token.value, token)
        elif token.kind == "LPAREN":
            left = self.expression()
            self.expect("RPAREN", "Parenthèse fermante ) manquante.")
        else:
            self.error("Une valeur, un texte, un nombre, une variable ou une expression entre parenthèses est attendu.", token)

        while self.cur().kind in self.precedence:
            op = self.cur()
            prec = self.precedence[op.kind]
            if prec < min_prec:
                break
            self.take()
            right = self.expression(prec + 1)
            left = Expr("BINARY", op.kind, op, left, right)
        return left


@dataclass
class Value:
    kind: str
    value: object


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self):
        self.variables = {}
        self.scopes = [self.variables]
        self.functions = {}
        self.call_depth = 0
        self.loop_steps = 0
        self.max_call_depth = 100
        self.max_loop_steps = 200000

    def fail(self, message, token, category="Erreur d'exécution"):
        raise BuKoError(message, token, category)

    def lookup(self, name, token):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        self.fail(f"La variable « {name} » n'existe pas. Vérifie son nom ou déclare-la avant usage.",
                  token, "Variable inconnue")

    def evaluate(self, expr):
        if expr.kind == "UNARY_MINUS":
            value = self.evaluate(expr.right)
            if value.kind != "nombre":
                self.fail("Le signe − unaire attend un nombre.", expr.token, "Erreur de type")
            return Value("nombre", -value.value)
        if expr.kind == "NUMBER":
            return Value("nombre", expr.value)
        if expr.kind == "TEXT":
            return Value("texte", expr.value)
        if expr.kind == "BOOLEAN":
            return Value("booleen", expr.value)
        if expr.kind == "VARIABLE":
            return self.lookup(expr.value, expr.token)
        if expr.kind == "CALL":
            if expr.value not in self.functions:
                self.fail(f"La fonction « {expr.value} » n'existe pas. Déclare-la avec FO avant de l'appeler.",
                          expr.token, "Fonction inconnue")
            fn = self.functions[expr.value]
            args = expr.args or []
            if len(args) != len(fn.params or []):
                self.fail(f"La fonction « {expr.value} » attend {len(fn.params or [])} argument(s), "
                          f"mais {len(args)} ont été fourni(s).", expr.token, "Erreur d'appel")
            if self.call_depth >= self.max_call_depth:
                self.fail("Limite de récursion atteinte (100 appels imbriqués).",
                          expr.token, "Limite d'exécution")
            values = [self.evaluate(arg) for arg in args]
            self.scopes.append(dict(zip(fn.params or [], values)))
            self.call_depth += 1
            try:
                self.run(fn.body, in_function=True)
            except ReturnSignal as signal:
                return signal.value
            finally:
                self.call_depth -= 1
                self.scopes.pop()
            self.fail(f"La fonction « {expr.value} » s'est terminée sans instruction RE retourner.",
                      expr.token, "Valeur de retour manquante")

        left = self.evaluate(expr.left)
        right = self.evaluate(expr.right)
        op = expr.value
        if op == "PLUS" and left.kind == right.kind == "texte":
            return Value("texte", left.value + right.value)
        if left.kind != "nombre" or right.kind != "nombre":
            self.fail("Cette opération attend deux nombres (sauf + entre deux textes).",
                      expr.token, "Erreur de type")
        if op == "PLUS":
            result = left.value + right.value
        elif op == "MINUS":
            result = left.value - right.value
        elif op == "MULTIPLY":
            result = left.value * right.value
        else:
            if right.value == 0:
                self.fail("Division par zéro. Vérifie le diviseur avant le calcul.", expr.token, "Erreur de calcul")
            result = left.value / right.value
            if result.is_integer():
                result = int(result)
        return Value("nombre", result)

    def evaluate_condition(self, terms, joiners):
        results = []
        for left_expr, operator, right_expr in terms:
            left, right = self.evaluate(left_expr), self.evaluate(right_expr)
            if left.kind != right.kind:
                self.fail("Les deux valeurs comparées doivent être du même type.", left_expr.token, "Erreur de type")
            if operator in ("GT", "LT", "GE", "LE") and left.kind != "nombre":
                self.fail("Les comparaisons >, <, ≥ et ≤ attendent deux nombres.", left_expr.token, "Erreur de type")
            if operator == "EQUALS": matched = left.value == right.value
            elif operator == "NE": matched = left.value != right.value
            elif operator == "GT": matched = left.value > right.value
            elif operator == "LT": matched = left.value < right.value
            elif operator == "GE": matched = left.value >= right.value
            else: matched = left.value <= right.value
            results.append(matched)
        grouped, current = [], results[0]
        for idx, joiner in enumerate(joiners or []):
            if joiner == "et": current = current and results[idx + 1]
            else:
                grouped.append(current)
                current = results[idx + 1]
        grouped.append(current)
        return any(grouped)

    def run(self, statements, in_function=False):
        output = []
        for stmt in statements:
            if stmt.kind == "function":
                if stmt.name in self.functions:
                    self.fail(f"La fonction « {stmt.name} » est déclarée plusieurs fois.", stmt.token, "Fonction dupliquée")
                self.functions[stmt.name] = stmt
        for stmt in statements:
            if stmt.kind == "function":
                continue
            if stmt.kind == "return":
                if not in_function:
                    self.fail("RE retourner ne peut être utilisé qu'à l'intérieur d'une fonction FO.", stmt.token, "Retour hors fonction")
                raise ReturnSignal(self.evaluate(stmt.expression))
            if stmt.kind == "declare":
                value = self.evaluate(stmt.expression)
                if value.kind != stmt.declared_type:
                    self.fail(f"Le type déclaré « {stmt.declared_type} » ne correspond pas au type « {value.kind} ».", stmt.token, "Erreur de type")
                self.scopes[-1][stmt.name] = value
            elif stmt.kind == "assign":
                target = next((scope for scope in reversed(self.scopes) if stmt.name in scope), None)
                if target is None:
                    self.fail(f"La variable « {stmt.name} » n'existe pas. Déclare-la avant de lui attribuer une valeur.", stmt.token, "Variable inconnue")
                value = self.evaluate(stmt.expression)
                if target[stmt.name].kind != value.kind:
                    self.fail("Le type de la nouvelle valeur doit correspondre au type de la variable.", stmt.token, "Erreur de type")
                target[stmt.name] = value
            elif stmt.kind == "display":
                shown = self.evaluate(stmt.expression).value
                output.append(str(shown))
            elif stmt.kind == "input":
                prompt = stmt.expression.value if stmt.expression is not None else f"Valeur pour {stmt.name} :"
                if not hasattr(self, "input_provider") or self.input_provider is None:
                    self.fail("EN saisir nécessite une interface de saisie. Dans BuKo Studio, une boîte de dialogue sera utilisée.", stmt.token, "Saisie indisponible")
                raw = self.input_provider(prompt)
                if raw is None:
                    self.fail("La saisie a été annulée.", stmt.token, "Saisie annulée")
                self.scopes[-1][stmt.name] = Value("texte", str(raw))
            elif stmt.kind == "condition":
                terms = stmt.condition_terms or [(stmt.condition_left, stmt.condition_operator, stmt.condition_right)]
                if self.evaluate_condition(terms, stmt.condition_joiners):
                    output.extend(self.run(stmt.body, in_function=in_function))
            elif stmt.kind == "loop":
                count = self.evaluate(stmt.loop_count)
                if count.kind != "nombre" or not isinstance(count.value, int):
                    self.fail("BO répéter attend un nombre entier de répétitions.", stmt.token, "Erreur de type")
                if count.value < 0:
                    self.fail("Le nombre de répétitions ne peut pas être négatif.", stmt.token, "Erreur de boucle")
                if count.value > 100000:
                    self.fail("Limite de sécurité : une boucle ne peut pas dépasser 100 000 répétitions.", stmt.token, "Limite d'exécution")
                for _ in range(count.value):
                    self.loop_steps += 1
                    if self.loop_steps > self.max_loop_steps:
                        self.fail("Limite de sécurité : trop d'itérations cumulées pendant ce programme.", stmt.token, "Limite d'exécution")
                    output.extend(self.run(stmt.body, in_function=in_function))
            elif stmt.kind == "while":
                iterations = 0
                while self.evaluate_condition(stmt.condition_terms, stmt.condition_joiners):
                    iterations += 1
                    self.loop_steps += 1
                    if iterations > 100000 or self.loop_steps > self.max_loop_steps:
                        self.fail("La boucle BO tant_que dépasse la limite de sécurité. Vérifie que sa condition peut devenir fausse.", stmt.token, "Limite d'exécution")
                    output.extend(self.run(stmt.body, in_function=in_function))
        return output


DEMO = (
    '# Démonstration BuKo v0.6\n'
    'texte nom = "Abraham".\n'
    "nombre age = 18'.\n"
    "FO doubler(x) {\n"
    "    RE retourner x × 2'.\n"
    "}\n"
    "AF afficher nom.\n"
    "AF afficher age.\n"
    "AF afficher doubler(10').\n"
    "nombre compteur = 0'.\n"
    "BO tant_que compteur < 3' {\n"
    "    AF afficher compteur.\n"
    "    compteur = compteur + 1'.\n"
    "}\n"
)

def execute(source, input_provider=None):
    tokens = Lexer(source).tokenize()
    tree = Parser(tokens).parse()
    interpreter = Interpreter()
    interpreter.input_provider = input_provider
    return interpreter.run(tree)


def main():
    cli = argparse.ArgumentParser(description="Moteur prototype BuKo v0.6")
    cli.add_argument("file", nargs="?", help="Fichier source .buko")
    cli.add_argument("--demo", action="store_true", help="Lancer le programme de démonstration")
    args = cli.parse_args()

    if args.demo:
        source, filename = DEMO, "<demo>"
    elif args.file:
        filename = args.file
        try:
            source = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Impossible de lire le fichier : {exc}", file=sys.stderr)
            return 2
    else:
        print("BuKo v0.6 — utilise --demo ou indique un fichier .buko.")
        print("Exemple : python buko_engine_v0_6.py --demo")
        return 0

    try:
        for line in execute(source):
            print(line)
        return 0
    except BuKoError as exc:
        print(exc.formatted(filename), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
