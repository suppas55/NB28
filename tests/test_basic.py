import pytest

def test_always_passes():
    """Basic test that always passes to ensure pytest runs successfully"""
    assert True

def test_simple_math():
    """Test basic arithmetic operations"""
    assert 2 + 2 == 4
    assert 3 * 3 == 9
    assert 10 - 5 == 5
    assert 20 / 4 == 5

def test_string_operations():
    """Test basic string operations"""
    assert "hello" + " " + "world" == "hello world"
    assert "python".upper() == "PYTHON"
    assert "TEST".lower() == "test"
    assert len("pytest") == 6

def test_list_operations():
    """Test basic list operations"""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert test_list[0] == 1
    assert test_list[-1] == 5
    assert sum(test_list) == 15

def test_dictionary_operations():
    """Test basic dictionary operations"""
    test_dict = {"a": 1, "b": 2, "c": 3}
    assert len(test_dict) == 3
    assert test_dict["a"] == 1
    assert "b" in test_dict
    assert "d" not in test_dict
