# Copyright 2024 Xanadu Quantum Technologies Inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module contains the classes for tensor views.
"""

from __future__ import annotations

#import numpy as np

from mrmustard import math
from mrmustard.utils.typing import Tensor, Matrix, Vector

__all__ = ["ArrayView", "ConjView"]

class ArrayView:
    r"""
    """
    def __init__(self, array: Tensor | Matrix | Vector, min_dim: int | None = None):
        self._array = array
        self._min_dim = min_dim

    def _get_array(self):
        if self._min_dim:
            return getattr(math, f"atleast_{self._min_dim}d")(self._array)
        return math.astensor(self._array)

    @property
    def array(self):
        r"""
        Returns 
        """
        return self._get_array()
    
    def conj(self):
        return ConjView(self._array, self._min_dim)
    

class ConjView(ArrayView):
    r"""
    """

    @property
    def array(self):
        r"""
        Returns 
        """
        return math.conj(self._get_array())
    
    def conj(self):
        return ArrayView(self._array, self._min_dim)