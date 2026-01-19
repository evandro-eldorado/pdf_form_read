# SPDX-FileCopyrightText: 2026 Evandro Chagas Ribeiro da Rosa <evandro.rosa.BE@eldorado.org.br>
#
# SPDX-License-Identifier: MIT
import re
from io import BytesIO
from pypdf import PdfReader
import pandas as pd
import ast
import logging

logging.disable(logging.CRITICAL)


def validate_py(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def read_row_fields(file):
    reader = PdfReader(file)

    fields = reader.get_fields()

    if not fields:
        raise ValueError("Fail to read PDF as a Form")
    else:
        return {name: value.get("/V") for name, value in fields.items()}


def format_cpf(cpf: str) -> str | None:
    cpf = re.sub(r"\D", "", cpf)

    if len(cpf) != 11:
        return None

    if cpf == cpf[0] * 11:
        return None

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digit1 = (soma * 10) % 11
    digit1 = 0 if digit1 == 10 else digit1

    if digit1 != int(cpf[9]):
        return None

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digit2 = (soma * 10) % 11
    digit2 = 0 if digit2 == 10 else digit2

    if digit2 != int(cpf[10]):
        return None

    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def question_number(question):
    return int(re.search(r"\d", question).group())


def read_questions(question: str, response: str):
    if "radio_group" in question:
        return question_number(question), response[1] if response is not None else None
    elif "num" in question:
        try:
            response = response.replace(",", ".")
            response = float(response)
            return question_number(question), response
        except Exception:
            return question_number(question), None
    elif "code" in question:
        return question_number(question), (validate_py(response), response)
    else:
        raise ValueError(f"Unknown question type {question}")


def process_row_field(fields: dict):
    return {
        "Pessoal": {
            "Nome": fields["header_nome"].strip().title(),
            "CPF": format_cpf(fields["header_cpf"]),
        },
        "Questões": dict(
            read_questions(q, r) for q, r in fields.items() if q[0] == "q"
        ),
    }


def dict_to_table(dados: dict) -> pd.DataFrame:
    line = []

    for campo, valor in dados.get("Pessoal", {}).items():
        line.append({"Item": campo, "Resposta": valor})

    for numero, resposta in dados.get("Questões", {}).items():
        line.append({"Item": f"Questão {numero}", "Resposta": resposta})

    return pd.DataFrame(line)


def verificar_pdf(upload_widget):
    try:
        file = upload_widget.value[0]
        file = file["content"]
        file = BytesIO(file)
        return dict_to_table(process_row_field(read_row_fields(file)))
    except Exception as e:
        print(
            "Não foi possível processar o arquivo PDF.\n"
            "Certifique-se de que o arquivo enviado está correto e que o documento foi salvo,\n"
            "e não gerado por meio de impressão virtual.\n"
        )
        print(f"Erro: {e}")
