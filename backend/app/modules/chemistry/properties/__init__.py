"""Provedores de propriedades moleculares (Web Lite v1).

Cada provedor recebe um PropertyContext e devolve um PropertyBundle com valores no
mesmo formato ParameterValue do painel. O orquestrador mescla esses valores na
resposta de /chemistry/parameters/analyze sem sobrescrever campos já disponíveis.
"""
