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

from __future__ import annotations
import numpy as np
from mrmustard.lab.representations.data.data import Data
from mrmustard.math import Math
from mrmustard.typing import Matrix, Scalar, Vector
from mrmustard.physics.gaussian import reorder_matrix_from_qpqp_to_qqpp

math = Math()

class MatVecData(Data):  # Note: this class is abstract too!
    r""" Contains matrix and vector -like data for certain Representation objects.

    Args:
        mat: the matrix-like data to be contained in the class
        vec: the vector-like data to be contained in the class
        coeffs: the coefficients 
    """

    def __init__(self, 
                 mat: Matrix,
                 vec: Vector,
                 coeffs: Scalar
                 ) -> None:
        self.mat = mat #math.atleast_3d(mat)
        self.vec = vec #math.atleast_2d(vec)
        self.coeffs = coeffs #math.atleast_1d(coeffs)


    def __neg__(self) -> MatVecData:
        new_coeffs = - self.coeffs
        return self.__class__(self.mat, self.vec, new_coeffs)


    def __eq__(self, other: MatVecData) -> bool:
        try: 
            return super().same(
                X = [self.mat, self.vec, self.coeffs],
                Y = [other.mat, other.vec, other.coeffs],
                )
        
        except AttributeError as e:
            raise TypeError(
                f"Cannot compare {self.__class__} and {other.__class__}.") from e


    def __add__(self, other: MatVecData) -> MatVecData:
        try:
            if super().same(X=[self.mat, self.vec], Y=[other.mat, other.vec]):
                combined_coeffs = self.coeffs + other.coeffs
                return self.__class__(self.mat, self.vec, combined_coeffs)
            
            else:
                    mat = math.concat([self.mat, other.mat], axis=0)
                    vec = math.concat([self.vec, other.vec], axis=0)
                    reorder_matrix = reorder_matrix_from_qpqp_to_qqpp(self.mat.shape[-1])
                    mat = math.matmul(math.matmul(reorder_matrix, mat), math.transpose(reorder_matrix))
                    vec = math.matvec(reorder_matrix, vec)
                    combined_coeffs = math.concat([self.coeffs, other.coeffs], axis=0)
                    return self.__class__(mat, vec, combined_coeffs)
                
        except AttributeError as e:
            raise TypeError(f"Cannot add/subtract {self.__class__} and {other.__class__}.") from e
        

    # def __and__(self, other: MatVecData) -> MatVecData:
    #     try: #TODO: ORDER OF ALL MATRICESA!
    #         mat = [math.block_diag([c1, c2]) for c1 in self.mat for c2 in other.mat]
    #         vec = [math.concat([v1, v2], axis= -1) for v1 in self.vec for v2 in other.vec]
    #         coeffs = [c1 * c2 for c1 in self.coeffs for c2 in other.coeffs]

    #         return self.__class__(math.astensor(mat), math.astensor(vec), math.astensor(coeffs))

    #     except AttributeError as e:
    #         raise TypeError(f"Cannot tensor {self.__class__} and {other.__class__}.") from e
        

    def __truediv__(self, x:Scalar) -> MatVecData:
        new_coeffs = self.coeffs/x
        return self.__class__(self.mat, self.vec, new_coeffs)
    # # TODO: decide which simplify we want to keep
    # def simplify(self, rtol:float=1e-6, atol:float=1e-6) -> MatVecData:
    #     N = self.mat.shape[0]
    #     mask = np.ones(N, dtype=np.int8)

    #     for i in range(N):

    #         for j in range(i + 1, N):

    #             if mask[i] == 0 or i == j:  # evaluated previously
    #                 continue

    #             if np.allclose(
    #                 self.mat[i], self.mat[j], rtol=rtol, atol=atol, equal_nan=True
    #             ) and np.allclose(
    #                 self.vec[i], self.vec[j], rtol=rtol, atol=atol, equal_nan=True
    #             ):
    #                 self.coeffs[i] += self.coeffs[j]
    #                 mask[j] = 0

    #     return self.__class__(
    #         mat = self.mat[mask == 1],
    #         vec = self.vec[mask == 1],
    #         coeffs = self.coeffs[mask == 1]
    #         )


    # # TODO: decide which simplify we want to keep
    # def old_simplify(self) -> None:
    #     indices_to_check = set(range(self.batch_size))
    #     removed = set()

    #     while indices_to_check:
    #         i = indices_to_check.pop()

    #         for j in indices_to_check.copy():
    #             if np.allclose(self.mat[i], self.mat[j]) and np.allclose(
    #                 self.vec[i], self.vec[j]
    #             ):
    #                 self.coeffs[i] += self.coeffs[j]
    #                 indices_to_check.remove(j)
    #                 removed.add(j)

    #     to_keep = [i for i in range(self.batch_size) if i not in removed]
    #     self.mat = self.mat[to_keep]
    #     self.vec = self.vec[to_keep]
    #     self.coeffs = self.coeffs[to_keep]