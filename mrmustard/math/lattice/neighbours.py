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
#

import numpy as np
from numba import njit

from mrmustard.types import Generator, Matrix, Vector

#################################################################################
## All neighbours means all the indices that differ from the given pivot by ±1 ##
#################################################################################


@njit
def all_neighbours_gen(pivot: Vector) -> Generator[Vector, None, None]:
    r"yields the indices of all the nearest neighbours of the given pivot"
    for i in range(len(pivot)):
        pivot[i] += 1
        yield pivot
        pivot[i] -= 2
        yield pivot
        pivot[i] += 1


@njit
def all_neighbours_fn(pivot: Vector) -> Matrix:
    r"returns the indices of the nearest neighbours of the given pivot as an array"
    Z = np.zeros((2 * len(pivot), len(pivot)), dtype=np.int64)
    for i, p in enumerate(pivot):
        pivot[i] += 1
        Z[2 * i] = pivot
        pivot[i] -= 2
        Z[2 * i + 1] = pivot
        pivot[i] += 1
    return Z


####################################################################################
## Lower neighbours means all the indices that differ from the given index by -1  ##
####################################################################################


@njit
def lower_neighbors_gen(pivot: Vector) -> Generator[Vector, None, None]:
    r"yields the indices of the lower neighbours of the given index"
    for i in range(len(pivot)):
        pivot[i] -= 1
        yield pivot
        pivot[i] += 1


@njit
def lower_neighbors_fn(pivot: Vector) -> Matrix:
    r"returns the indices of the lower neighbours of the given index as an array"
    Z = np.zeros((len(pivot), len(pivot)), dtype=np.int64)
    for i, p in enumerate(pivot):
        pivot[i] -= 1
        Z[i] = pivot
        pivot[i] += 1
    return Z


####################################################################################
## Upper neighbours means all the indices that differ from the given index by +1  ##
####################################################################################


@njit
def upper_neighbors_gen(pivot: Vector) -> Generator[Vector, None, None]:
    r"yields the indices of the upper neighbours of the given pivot"
    for i in range(len(pivot)):
        pivot[i] += 1
        yield pivot
        pivot[i] -= 1


@njit
def upper_neighbors_fn(pivot: Vector) -> Matrix:
    r"returns the indices of the upper neighbours of the given index as an array"
    Z = np.zeros((len(pivot), len(pivot)), dtype=np.int64)
    for i, p in enumerate(pivot):
        pivot[i] -= 1
        Z[i] = pivot
        pivot[i] += 1
    return Z


####################################################################################################
## bitstring neighbours are indices that differ from the given index by ±1 according to a bitstring
####################################################################################################


@njit
def bitstring_neighbours_gen(pivot: Vector, bitstring: Vector) -> Generator[Vector, None, None]:
    r"yields the indices of the bitstring neighbours of the given index"
    for i, b in enumerate(bitstring):
        if b:
            pivot[i] -= 1
            yield pivot
            pivot[i] += 1
        else:
            pivot[i] += 1
            yield pivot
            pivot[i] -= 1
