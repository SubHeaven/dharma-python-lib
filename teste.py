# -*- coding: utf-8 -*-
import os
import sys
import lib.tools as tools

from lib.arg_parser import *

@arg_parser(".".join(os.path.basename(__file__).split(".")[0:-1]), 'Teste para analisar o sequencial de notas de uma empresa')
# @positional_param('salute', 'Tipo de saudação.', sample='Bom dia', required=False, options=['Bom dia', 'Boa tarde', 'Boa noite'])
# @positional_param('nome', 'Nome de quem será cumprimentado.', required=False, sample='mundo')
@named_param('empresa', 'Código da empresa.', sample='1387', required=False)
# @named_param('competencia', 'Indica a competência a ser processada. Se não for informada, processa a competência atual.', sample='202112', required=False)
# @named_param('anoini', 'Ano inicial. Se não for informado, processa o ano atual.', sample='2020', required=False)
# @boolean_param('debug', 'Mostra apenas os dados de calculo de sequencial')
def processar():
    tools.debug(params)

if __name__ == "__main__":
    processar()