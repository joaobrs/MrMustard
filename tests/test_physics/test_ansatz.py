# Copyright 2023 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
from hypothesis import given
import pytest

from mrmustard import math
from mrmustard.physics.ansatze import PolyExpAnsatz, ArrayAnsatz
from tests.random import Abc_triple, complex_number


@given(Abc=Abc_triple())
def test_PolyExpAnsatz(Abc):
    """Test that the PolyExpAnsatz class is initialized correctly"""
    A, b, c = Abc
    ansatz = PolyExpAnsatz(A, b, c)
    assert np.allclose(ansatz.mat[0], A)
    assert np.allclose(ansatz.vec[0], b)
    assert np.allclose(ansatz.array[0], c)


# test adding two PolyExpAnsatz objects
@given(Abc1=Abc_triple(5), Abc2=Abc_triple(5))
def test_PolyExpAnsatz_add(Abc1, Abc2):
    """Test that we can add two PolyExpAnsatz objects"""
    A1, b1, c1 = Abc1
    A2, b2, c2 = Abc2
    ansatz = PolyExpAnsatz(A1, b1, c1)
    ansatz2 = PolyExpAnsatz(A2, b2, c2)
    ansatz3 = ansatz + ansatz2
    assert np.allclose(ansatz3.mat[0], A1)
    assert np.allclose(ansatz3.vec[0], b1)
    assert np.allclose(ansatz3.array[0], c1)
    assert np.allclose(ansatz3.mat[1], A2)
    assert np.allclose(ansatz3.vec[1], b2)
    assert np.allclose(ansatz3.array[1], c2)


# test multiplying two PolyExpAnsatz objects
@given(Abc1=Abc_triple(4), Abc2=Abc_triple(4))
def test_PolyExpAnsatz_mul(Abc1, Abc2):
    """Test that we can multiply two PolyExpAnsatz objects"""
    A1, b1, c1 = Abc1
    A2, b2, c2 = Abc2
    ansatz = PolyExpAnsatz(A1, b1, c1)
    ansatz2 = PolyExpAnsatz(A2, b2, c2)
    ansatz3 = ansatz * ansatz2
    assert np.allclose(ansatz3.mat[0], A1 + A2)
    assert np.allclose(ansatz3.vec[0], b1 + b2)
    assert np.allclose(ansatz3.array[0], c1 * c2)


# test multiplying a PolyExpAnsatz object by a scalar
@given(Abc=Abc_triple(), d=complex_number)
def test_PolyExpAnsatz_mul_scalar(Abc, d):
    """Test that we can multiply a PolyExpAnsatz object by a scalar"""
    A, b, c = Abc
    ansatz = PolyExpAnsatz(A, b, c)
    ansatz2 = ansatz * d
    assert np.allclose(ansatz2.mat[0], A)
    assert np.allclose(ansatz2.vec[0], b)
    assert np.allclose(ansatz2.array[0], d * c)


# test calling the PolyExpAnsatz object
@given(Abc=Abc_triple())
def test_PolyExpAnsatz_call(Abc):
    """Test that we can call the PolyExpAnsatz object"""
    A, b, c = Abc
    ansatz = PolyExpAnsatz(A, b, c)
    assert np.allclose(ansatz(z=math.zeros_like(b)), c)


# test tensor product of two PolyExpAnsatz objects
@given(Abc1=Abc_triple(6), Abc2=Abc_triple(6))
def test_PolyExpAnsatz_kron(Abc1, Abc2):
    """Test that we can tensor product two PolyExpAnsatz objects"""
    A1, b1, c1 = Abc1
    A2, b2, c2 = Abc2
    ansatz = PolyExpAnsatz(A1, b1, c1)
    ansatz2 = PolyExpAnsatz(A2, b2, c2)
    ansatz3 = ansatz & ansatz2
    assert np.allclose(ansatz3.mat[0], math.block_diag(A1, A2))
    assert np.allclose(ansatz3.vec[0], math.concat([b1, b2], -1))
    assert np.allclose(ansatz3.array[0], c1 * c2)


# test equality
@given(Abc=Abc_triple())
def test_PolyExpAnsatz_eq(Abc):
    """Test that we can compare two PolyExpAnsatz objects"""
    A, b, c = Abc
    ansatz = PolyExpAnsatz(A, b, c)
    ansatz2 = PolyExpAnsatz(2 * A, 2 * b, 2 * c)
    assert ansatz == ansatz
    assert ansatz2 == ansatz2
    assert ansatz != ansatz2
    assert ansatz2 != ansatz


# test simplify
@given(Abc=Abc_triple())
def test_PolyExpAnsatz_simplify(Abc):
    """Test that we can simplify a PolyExpAnsatz object"""
    A, b, c = Abc
    ansatz = PolyExpAnsatz(A, b, c)
    ansatz = ansatz + ansatz
    assert np.allclose(ansatz.A[0], ansatz.A[1])
    assert np.allclose(ansatz.A[0], A)
    assert np.allclose(ansatz.b[0], ansatz.b[1])
    assert np.allclose(ansatz.b[0], b)
    ansatz.simplify()
    assert len(ansatz.A) == 1
    assert len(ansatz.b) == 1
    assert ansatz.c == 2 * c


def test_order_batch():
    ansatz = PolyExpAnsatz(
        A=[np.array([[0]]), np.array([[1]])], b=[np.array([1]), np.array([0])], c=[1, 2]
    )
    ansatz._order_batch()
    assert np.allclose(ansatz.A[0], np.array([[1]]))
    assert np.allclose(ansatz.b[0], np.array([0]))
    assert ansatz.c[0] == 2
    assert np.allclose(ansatz.A[1], np.array([[0]]))
    assert np.allclose(ansatz.b[1], np.array([1]))
    assert ansatz.c[1] == 1


@given(Abc=Abc_triple())
def test_PolyExpAnsatz_simplify_v2(Abc):
    """Test that we can simplify a PolyExpAnsatz object"""
    A, b, c = Abc
    ansatz = PolyExpAnsatz(A, b, c)
    ansatz = ansatz + ansatz
    assert np.allclose(ansatz.A[0], ansatz.A[1])
    assert np.allclose(ansatz.A[0], A)
    assert np.allclose(ansatz.b[0], ansatz.b[1])
    assert np.allclose(ansatz.b[0], b)
    ansatz.simplify_v2()
    assert len(ansatz.A) == 1
    assert len(ansatz.b) == 1
    assert np.allclose(ansatz.c, 2 * c)


class TestArrayAnsatz:
    r"""Tests all algebra related to ArrayAnsatz."""

    def test_ArrayAnsatz_init_(self):
        r"""Tests that an ArrayAnstaz can be initialized."""
        array = np.random.random((2, 4, 5))
        aa = ArrayAnsatz(array=array)
        assert isinstance(aa, ArrayAnsatz)
        assert np.allclose(aa.array, array)

    def test_ArrayAnsatz_neg(self):
        r"""Negates the array inside ArrayAnsatz."""
        array = np.random.random((2, 4, 5))
        aa = ArrayAnsatz(array=array)
        minusaa = -aa
        assert isinstance(minusaa, ArrayAnsatz)
        assert np.allclose(minusaa.array, -array)

    def test_ArrayAnsatz_equal(self):
        r"""Tests the equation of two ArrayAnsatzs."""
        array = np.random.random((2, 4, 5))
        aa1 = ArrayAnsatz(array=array)
        aa2 = ArrayAnsatz(array=array)
        assert aa1 == aa2

    def test_ArrayAnsatz_addition(self):
        r"""Tests the correctness of adding two ArrayAnsatzs."""
        array = np.random.random((2, 4, 5))
        array2 = np.random.random((4, 4, 5))
        aa1 = ArrayAnsatz(array=array)
        aa2 = ArrayAnsatz(array=array2)
        aa1_add_aa2 = aa1 + aa2
        assert isinstance(aa1_add_aa2, ArrayAnsatz)
        assert aa1_add_aa2.array.shape == (8, 4, 5)

    def test_ArrayAnsatz_and(self):
        r"""Tests the correctness of adding two ArrayAnsatzs."""
        array = np.random.random((2, 4, 5))
        array2 = np.random.random((7, 4, 5))
        aa1 = ArrayAnsatz(array=array)
        aa2 = ArrayAnsatz(array=array2)
        aa1_and_aa2 = aa1 & aa2
        assert isinstance(aa1_and_aa2, ArrayAnsatz)
        assert aa1_and_aa2.array.shape == (14, 4, 5, 4, 5)

    def test_ArrayAnsatz_multiply_with_a_scalar(self):
        r"""Tests the correctness of multiplying an ArrayAnsatz with a scalar."""
        array = np.random.random((2, 4, 5))
        aa1 = ArrayAnsatz(array=array)
        aa1_scalar = aa1 * 8
        assert isinstance(aa1_scalar, ArrayAnsatz)
        assert np.allclose(aa1_scalar.array, array * 8)

    def test_ArrayAnsatz_mul(self):
        r"""Tests the correctness of multiplying two ArrayAnsatzs."""
        array = np.random.random((2, 4, 5))
        array2 = np.random.random((3, 4, 5))
        aa1 = ArrayAnsatz(array=array)
        aa2 = ArrayAnsatz(array=array2)
        aa1_mul_aa2 = aa1 * aa2
        assert isinstance(aa1_mul_aa2, ArrayAnsatz)
        assert aa1_mul_aa2.array.shape == (6, 4, 5)

    def test_ArrayAnsatz_divide_by_a_scalar(self):
        r"""Tests the correctness of dividing an ArrayAnsatz with a scalar."""
        array = np.random.random((2, 4, 5))
        aa1 = ArrayAnsatz(array=array)
        aa1_scalar = aa1 / 6
        assert isinstance(aa1_scalar, ArrayAnsatz)
        assert np.allclose(aa1_scalar.array, array / 6)

    def test_ArrayAnsatz_div(self):
        r"""Tests the correctness of multiplying two ArrayAnsatzs."""
        array = np.random.random((2, 4, 5))
        array2 = np.random.random((3, 4, 5))
        aa1 = ArrayAnsatz(array=array)
        aa2 = ArrayAnsatz(array=array2)
        aa1_div_aa2 = aa1 / aa2
        assert isinstance(aa1_div_aa2, ArrayAnsatz)
        assert aa1_div_aa2.array.shape == (6, 4, 5)

    def test_Array_Ansatz_algebra_with_different_shape_of_array_raise_errors(self):
        r"""Tests the errors are raised correctly."""
        array = np.random.random((2, 4, 5))
        array2 = np.random.random((3, 4, 8, 9))
        aa1 = ArrayAnsatz(array=array)
        aa2 = ArrayAnsatz(array=array2)
        with pytest.raises(Exception):
            aa1 + aa2
        with pytest.raises(Exception):
            aa1 - aa2
        with pytest.raises(Exception):
            aa1 * aa2
        with pytest.raises(Exception):
            aa1 / aa2
        with pytest.raises(Exception):
            aa1 == aa2
