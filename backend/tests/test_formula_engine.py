from decimal import Decimal
import pytest
from app.services.formula_engine import evaluate_formula, FormulaError


def test_simple_arithmetic():
    assert evaluate_formula("2 + 3 * 4", {}) == Decimal(14)


def test_name_resolution():
    assert evaluate_formula("contract_wage / 2", {"contract_wage": Decimal(50000)}) == Decimal(25000)


def test_rules_subscript():
    ctx = {"rules": {"BASIC": Decimal(25000)}, "categories": {}}
    assert evaluate_formula('rules["BASIC"] * 0.2', ctx) == Decimal("5000.0")


def test_categories_subscript():
    ctx = {"rules": {}, "categories": {"GROSS": Decimal(32000)}}
    assert evaluate_formula('categories["GROSS"] - 2500', ctx) == Decimal("29500")


def test_unknown_variable_rejected():
    with pytest.raises(FormulaError, match="Unknown variable"):
        evaluate_formula("undefined_var + 1", {})


def test_unknown_rule_code_rejected():
    with pytest.raises(FormulaError, match="Unknown rule code"):
        evaluate_formula('rules["MISSING"]', {"rules": {}, "categories": {}})


def test_function_call_rejected():
    with pytest.raises(FormulaError, match="not allowed"):
        evaluate_formula("abs(-5)", {})


def test_attribute_access_rejected():
    with pytest.raises(FormulaError, match="not allowed"):
        evaluate_formula("contract_wage.__class__", {"contract_wage": Decimal(1)})


def test_import_like_syntax_rejected():
    with pytest.raises(FormulaError):
        evaluate_formula("__import__('os').system('ls')", {})


def test_arbitrary_subscript_target_rejected():
    with pytest.raises(FormulaError, match="Only rules"):
        evaluate_formula('other["x"]', {"other": {"x": 1}})


def test_non_string_subscript_key_rejected():
    with pytest.raises(FormulaError, match="string literal"):
        evaluate_formula("rules[1]", {"rules": {1: Decimal(1)}, "categories": {}})


def test_division_by_zero_raises_formula_error():
    with pytest.raises(FormulaError, match="Arithmetic error"):
        evaluate_formula("5 / 0", {})


def test_invalid_syntax_raises_formula_error():
    with pytest.raises(FormulaError, match="Invalid formula syntax"):
        evaluate_formula("2 + ", {})
