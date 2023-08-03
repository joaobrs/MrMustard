# Copyright 2021 Xanadu Quantum Technologies Inc.

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
import pytest

from mrmustard.lab.representations.wigner_dm import WignerDM


class TestWignerDMThrowErrors:
    wignerdm = WignerDM(
        symplectic=np.random.random((2, 3, 3)), displacement=np.random.random(3), coeffs=1.0
    )

    def test_purity_with_error(self):
        with self.assertRaises(NotImplementedError):
            self.wignerdm.purity