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
""" This class corresponds to test child class for the MatVecData class.

Unlike some of its -abstract- parent test classes, this class is meant to be run with pytest.

Check parents test classe-s for more details on the rationale.

The fixtures for PARAMS, DATA and OTHER must correspond to the concrete class being tested, here
MatVecData.
"""

import numpy as np
import operator as op
import pytest

from copy import deepcopy

from mrmustard.typing import Matrix, Scalar, Vector
from mrmustard.utils.misc_tools import general_factory
from mrmustard.lab.representations.data.matvec_data import MatVecData


#########   Instantiating class to test  #########

@pytest.fixture
def MAT() -> Matrix:
    return np.eye(10) * 42

@pytest.fixture
def VEC() -> Vector:
    return np.ones(10) * 42

@pytest.fixture
def COEFFS() -> Scalar:
    return 42

@pytest.fixture
def TYPE():
    return MatVecData

@pytest.fixture
def PARAMS(COV, MEANS, COEFFS) -> dict:
    r"""Parameters for the class instance which is created."""
    params_dict = {'mat': MAT, 'vec': VEC, 'coeffs':COEFFS}
    return params_dict


@pytest.fixture()
def DATA(TYPE, PARAMS) -> MatVecData:
    r"""Instance of the class that must be tested."""
    return general_factory(TYPE, **PARAMS)


@pytest.fixture()
def OTHER(DATA) -> MatVecData:
    r"""Another instance of the class that must be tested."""
    return deepcopy(DATA)



class TestMatVecData(): #TODO: import parent!
    
    #########   Common to different methods  #########


    ####################  Init  ######################

    def if_coeffs_not_given_they_are_equal_to_1(self, TYPE, PARAMS):
        params_without_coeffs = deepcopy(PARAMS)
        del params_without_coeffs['coeffs']
        new_data = general_factory(TYPE, params_without_coeffs)
        assert new_data.c == 1
        

    ##################  Negative  ####################

    def test_negative_returns_new_object_with_neg_coeffs_and_unaltered_mat_and_vec(self, DATA):
        pre_op_data = deepcopy(DATA)
        neg_data = - DATA
        manual_neg_coeffs = - pre_op_data.coeffs
        assert manual_neg_coeffs == neg_data.coeffs
        assert np.allclose(neg_data.mat, pre_op_data.mat)
        assert np.allclose(neg_data.vec, pre_op_data.vec)


    ##################  Equality  ####################
    # TODO test?

    ##################  Addition  ####################
    # TODO: more complex tests of the general concat case!
    # @pytest.mark.parametrize("operator", [op.add, op.mul]) # op.truediv, op.mul
    # def test_when_mat_and_vec_same_coefs_get_element_wise_operation(self, operator, DATA, OTHER):
    #     pre_op_data = deepcopy(DATA)
    #     processed_data = operator(DATA,OTHER)
    #     assert operator(DATA.coeffs, OTHER.coeffs) == processed_data.coeffs
    #     assert np.allclose(DATA.mat, pre_op_data.mat)
    #     assert np.allclose(DATA.means, pre_op_data.means)


    ################  Subtraction  ###################
    # NOTE : tested via add and neg

    #############  Scalar division  ##################
    @pytest.mark.parametrize("operator", [op.truediv]) # op.truediv, op.mul
    @pytest.mark.parametrize('x', [2])
    def test_truediv_divides_coeffs_leaves_all_else_unaltered(self, DATA, operator, x):
        pre_op_data = deepcopy(DATA)
        divided_data = operator(DATA,x)
        self._helper_mat_vec_are_same_computed_coeffs_are_correct(divided_data, 
                                                                  pre_op_data, 
                                                                  operator, 
                                                                  x)

        

    ###############  Multiplication  ##################

    def test_new_object_resulting_from_mul_has_same_shape(self):
        pass

    def test_object_mul_when_matrix_and_vector_are_same_coeffs_get_multiplied(self):
        pass

    def test_object_mul_when_matrix_and_vector_are_same_only_coeffs_get_multiplied(self):
        pass

    def test_scalar_mul_multiplies_coeffs(self):
        pass

    def test_scalar_mul_only_multiplies_coeffs(self):
        pass


    ###############  Outer product  ##################
    # TODO: write tests


    ###############  Outer product  ##################

    
    def _helper_coeffs_are_computed_correctly(self, new_data_object, old_data_object, operator, x
                                              ) -> None:
        manually_computed_coeffs = operator(old_data_object.coeffs, x)
        assert np.allclose(new_data_object.coeffs, manually_computed_coeffs)

    def _helper_mat_vec_are_same_computed_coeffs_are_correct(self, new_data_object, old_data_object, operator, x
                                             ) -> None:
        self._helper_coeffs_are_computed_correctly(new_data_object, old_data_object, operator, x)
        assert np.allclose(new_data_object.mat, old_data_object.mat)
        assert np.allclose(new_data_object.means, old_data_object.means)
