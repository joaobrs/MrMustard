from __future__ import annotations
from mrmustard.backends import BackendInterface
from mrmustard._typing import *
from math import pi, sqrt
from thewalrus.quantum import is_pure_cov


class XPTensor:
    r"""A representation of tensors in phase space."""

    _backend: BackendInterface

    def __init__(self, modes: List[int], tensor: Optional[Tensor], zero_based: bool = False) -> None:
        if tensor is None:
            if zero_based:
                tensor = self._backend.zeros((2, len(modes), 2, len(modes)))
            else:
                tensor = self._backend.reshape(self._backend.eye(2*len(modes)), (2, len(modes), 2, len(modes)))
        if len(tensor.shape) < 4:
            raise ValueError("Tensor must have at least 4 dimensions")
        if tensor.shape[0] != 2 and tensor.shape[2] != 2 and tensor.shape[3] != tensor.shape[1]:
            raise ValueError("Tensor must have shape (2, N, 2, N)")
        if not isinstance(modes, List):
            raise TypeError("modes must be a List of ints")
        self.nmodes = len(modes)
        self.modes = modes
        self._tensor = tensor
        self.zero_based = zero_based
    
    @classmethod
    def from_xpxp(cls, xpxp_matrix: Matrix, modes: List[int], zero_based: bool=False) -> XPTensor:
        # internal representation has shape (2, N, 2, N)
        if xpxp_matrix is not None:
            xpxp_matrix = cls._backend.reshape(xpxp_matrix, (len(modes), 2, len(modes), 2))
            xpxp_matrix = cls._backend.transpose(xpxp_matrix, (1, 0, 3, 2))
        return XPTensor(modes, xpxp_matrix, zero_based)

    @classmethod
    def from_xxpp(cls, xxpp_matrix: Matrix, modes: List[int], zero_based: bool=False) -> XPTensor:
        # internal representation has shape (2, N, 2, N)
        if xxpp_matrix is not None:
            xxpp_matrix = cls._backend.reshape(xxpp_matrix, (2, len(modes), 2, len(modes)))
        return XPTensor(modes, xxpp_matrix, zero_based)

    def to_xpxp(self) -> Matrix:
        transposed = self._backend.transpose(self._tensor, (0, 1, 3, 2))
        return self._backend.reshape(transposed, (2*len(self.modes), 2*len(self.modes)))

    def to_xxpp(self) -> Matrix:
        return self._backend.reshape(self._tensor, (2*len(self.modes), 2*len(self.modes)))

    def empty(self, modes: List[int], zero_based: bool) -> XPTensor:
        if zero_based:
            base = self._backend.zeros((2*len(modes), 2*len(modes)))
        else:
            base = self._backend.eye(2*len(modes))
        return XPTensor(modes, self._backend.reshape(base, (2, len(modes), 2, len(modes))), zero_based)

    def reorder_modes(self, perm: List[int]):
        if len(perm) != self.nmodes:
            raise ValueError(f"permutation must have length {self.nmodes}")
        if not all(i in range(self.nmodes) for i in perm):
            raise ValueError("permutation must be a permutation of the modes")
        if perm == list(range(self.nmodes)):
            return self
        self._tensor = self._backend.gather(self._backend.gather(self._tensor, perm, axis=1), perm, axis=3)
        self.modes = [self.modes[i] for i in perm]

    def __mul__(self, other: XPTensor) -> XPTensor:
        empty = self.empty(sorted(list(set(self.modes) | set(other.modes))), self.zero_based or other.zero_based)
        after_self = self._backend.right_matmul_at_modes(empty.to_xxpp(), self.to_xxpp(), modes=self.modes)
        after_other = self._backend.right_matmul_at_modes(after_self, other.to_xxpp(), modes=other.modes)
        return XPTensor.from_xxpp(after_other, empty.modes, self.zero_based)

    def __add__(self, other: XPTensor) -> XPTensor:
        all_modes = sorted(list(set(self.modes) | set(other.modes)))
        zeros = self._backend.zeros((2 * len(all_modes), 2 * len(all_modes)))
        after_self = self._backend.add_at_modes(zeros, self.to_xxpp(), self.modes)
        after_other = self._backend.add_at_modes(after_self, other.to_xxpp(), other.modes)
        return XPTensor.from_xxpp(after_other, all_modes, self.zero_based)

    def __repr__(self) -> str:
        return repr(self._tensor)

    def __getitem__(self, item: Union[int, slice, List[int]]) -> XPTensor:
        if isinstance(item, int):
            return XPTensor([item], self._tensor[:, item, :, item][:, None, :, None], self.zero_based)
        elif isinstance(item, slice):
            return XPTensor(list(range(item.start, item.stop)), self._tensor[:, item, :, item], self.zero_based)
        elif isinstance(item, List):
            return XPTensor(item, self._backend.gather(self._backend.gather(self._tensor, item, axis=1), item, axis=3), self.zero_based)
        else:
            raise TypeError("Invalid index type")

    @property
    def T(self) -> XPTensor:
        return XPTensor(self.modes, self._backend.transpose(self._tensor, (0, 2, 1, 3)), self.zero_based)



class GaussianPlugin:
    r"""
    A plugin for all things Gaussian.

    The GaussianPlugin implements:
      - Gaussian states (pure and mixed)
      - Gaussian mixture states [upcoming]
      - Gaussian unitary transformations
      - Gaussian CPTP channels
      - Gaussian CP channels [upcoming]
      - Gaussian entropies [upcoming]
      - Gaussian entanglement [upcoming]
    """
    _backend: BackendInterface

    #  ~~~~~~
    #  States
    #  ~~~~~~

    def vacuum_state(self, num_modes: int, hbar: float) -> Tuple[Matrix, Vector]:
        r"""Returns the real covariance matrix and real means vector of the vacuum state.
        Args:
            num_modes (int): number of modes
            hbar (float): value of hbar
        Returns:
            Matrix: vacuum covariance matrix
            Vector: vacuum means vector
        """
        cov = self._backend.eye(num_modes * 2, dtype=self._backend.float64) * hbar / 2
        means = self._backend.zeros([num_modes * 2], dtype=self._backend.float64)
        return cov, means

    def coherent_state(self, x: Vector, y: Vector, hbar: float) -> Tuple[Matrix, Vector]:
        r"""Returns the real covariance matrix and real means vector of a coherent state.
        The dimension depends on the dimensions of x and y.
        Args:
            x (vector): real part of the means vector
            y (vector): imaginary part of the means vector
            hbar: value of hbar
        Returns:
            Matrix: coherent state covariance matrix
            Vector: coherent state means vector
        """
        x = self._backend.atleast_1d(x)
        y = self._backend.atleast_1d(y)
        num_modes = x.shape[-1]
        cov = self._backend.eye(num_modes * 2, dtype=x.dtype) * hbar / 2
        means = self._backend.concat([x, y], axis=0) * self._backend.sqrt(2 * hbar, dtype=x.dtype)
        return cov, means

    def squeezed_vacuum_state(self, r: Vector, phi: Vector, hbar: float) -> Tuple[Matrix, Vector]:
        r"""Returns the real covariance matrix and real means vector of a squeezed vacuum state.
        The dimension depends on the dimensions of r and phi.
        Args:
            r (vector): squeezing magnitude
            phi (vector): squeezing angle
            hbar: value of hbar
        Returns:
            Matrix: squeezed state covariance matrix
            Vector: squeezed state means vector
        """
        S = self.squeezing_symplectic(r, phi)
        cov = self._backend.matmul(S, self._backend.transpose(S)) * hbar / 2
        means = self._backend.zeros(cov.shape[-1], dtype=cov.dtype)
        return cov, means

    def thermal_state(self, nbar: Vector, hbar: float) -> Tuple[Matrix, Vector]:
        r"""Returns the real covariance matrix and real means vector of a thermal state.
        The dimension depends on the dimensions of nbar.
        Args:
            nbar (vector): average number of photons per mode
            hbar: value of hbar
        Returns:
            Matrix: thermal state covariance matrix
            Vector: thermal state means vector
        """
        g = self._backend.astensor((2 * nbar + 1) * hbar / 2)
        cov = self._backend.diag(self._backend.concat([g, g], axis=-1))
        means = self._backend.zeros(cov.shape[-1], dtype=cov.dtype)
        return cov, means

    def displaced_squeezed_state(self, r: Vector, phi: Vector, x: Vector, y: Vector, hbar: float) -> Tuple[Matrix, Vector]:
        r"""Returns the real covariance matrix and real means vector of a displaced squeezed state.
        The dimension depends on the dimensions of r, phi, x and y.
        Args:
            r   (scalar or vector): squeezing magnitude
            phi (scalar or vector): squeezing angle
            x   (scalar or vector): real part of the means
            y   (scalar or vector): imaginary part of the means
            hbar: value of hbar
        Returns:
            Matrix: displaced squeezed state covariance matrix
            Vector: displaced squeezed state means vector
        """
        S = self.squeezing_symplectic(r, phi)
        cov = self._backend.matmul(S, self._backend.transpose(S)) * hbar / 2
        means = self._backend.concat([x, y], axis=-1)
        return cov, means

    # ~~~~~~~~~~~~~~~~~~~~~~~~
    #  Unitary transformations
    # ~~~~~~~~~~~~~~~~~~~~~~~~

    def rotation_symplectic(self, angle: Union[Scalar, Vector]) -> Matrix:
        r"""Symplectic matrix of a rotation gate.
        The dimension depends on the dimension of the angle.
        Args:
            angle (scalar or vector): rotation angles
        Returns:
            Tensor: symplectic matrix of a rotation gate
        """
        angle = self._backend.atleast_1d(angle)
        num_modes = angle.shape[-1]
        x = self._backend.cos(angle)
        y = self._backend.sin(angle)
        return (
            self._backend.diag(self._backend.concat([x, x], axis=0))
            + self._backend.diag(-y, k=num_modes)
            + self._backend.diag(y, k=-num_modes)
        )

    def squeezing_symplectic(self, r: Union[Scalar, Vector], phi: Union[Scalar, Vector]) -> Matrix:
        r"""Symplectic matrix of a squeezing gate.
        The dimension depends on the dimension of r and phi.
        Args:
            r (scalar or vector): squeezing magnitude
            phi (scalar or vector): rotation parameter
        Returns:
            Tensor: symplectic matrix of a squeezing gate
        """
        r = self._backend.atleast_1d(r)
        phi = self._backend.atleast_1d(phi)
        num_modes = phi.shape[-1]
        cp = self._backend.cos(phi)
        sp = self._backend.sin(phi)
        ch = self._backend.cosh(r)
        sh = self._backend.sinh(r)
        return (
            self._backend.diag(self._backend.concat([ch - cp * sh, ch + cp * sh], axis=0))
            + self._backend.diag(-sp * sh, k=num_modes)
            + self._backend.diag(-sp * sh, k=-num_modes)
        )

    def displacement(self, x: Union[Scalar, Vector], y: Union[Scalar, Vector], hbar: float) -> Vector:
        r"""Returns the displacement vector for a displacement by alpha = x + iy.
        The dimension depends on the dimensions of x and y.
        Args:
            x (scalar or vector): real part of displacement
            y (scalar or vector): imaginary part of displacement
            hbar: value of hbar
        Returns:
            Vector: displacement vector of a displacement gate
        """
        x = self._backend.atleast_1d(x)
        y = self._backend.atleast_1d(y)
        if x.shape[-1] == 1:
            x = self._backend.tile(x, y.shape)
        if y.shape[-1] == 1:
            y = self._backend.tile(y, x.shape)
        return self._backend.sqrt(2 * hbar, dtype=x.dtype) * self._backend.concat([x, y], axis=0)

    def beam_splitter_symplectic(self, theta: Scalar, phi: Scalar) -> Matrix:
        r"""Symplectic matrix of a Beam-splitter gate.
        The dimension is 4x4.
        Args:
            theta: transmissivity parameter
            phi: phase parameter
        Returns:
            Matrix: symplectic (orthogonal) matrix of a beam-splitter gate
        """
        ct = self._backend.cos(theta)
        st = self._backend.sin(theta)
        cp = self._backend.cos(phi)
        sp = self._backend.sin(phi)
        zero = self._backend.zeros_like(theta)
        return self._backend.astensor(
            [
                [ct, -cp * st, zero, -sp * st],
                [cp * st, ct, -sp * st, zero],
                [zero, sp * st, ct, -cp * st],
                [sp * st, zero, cp * st, ct],
            ]
        )

    def mz_symplectic(self, phi_a: Scalar, phi_b: Scalar, internal: bool = False) -> Matrix:
        r"""Symplectic matrix of a Mach-Zehnder gate.
        It supports two conventions:
        if `internal=True`, both phases act inside the interferometer:
            `phi_a` on the upper arm, `phi_b` on the lower arm;
        if `internal = False` (default), both phases act on the upper arm:
            `phi_a` before the first BS, `phi_b` after the first BS.
        Args:
            phi_a (float): first phase
            phi_b (float): second phase
            internal (bool): whether phases are in the internal arms (default is False)
        Returns:
            Matrix: symplectic (orthogonal) matrix of a Mach-Zehnder interferometer
        """
        ca = self._backend.cos(phi_a)
        sa = self._backend.sin(phi_a)
        cb = self._backend.cos(phi_b)
        sb = self._backend.sin(phi_b)
        cp = self._backend.cos(phi_a + phi_b)
        sp = self._backend.sin(phi_a + phi_b)

        if internal:
            return 0.5 * self._backend.astensor(
                [
                    [ca - cb, -sa - sb, sb - sa, -ca - cb],
                    [-sa - sb, cb - ca, -ca - cb, sa - sb],
                    [sa - sb, ca + cb, ca - cb, -sa - sb],
                    [ca + cb, sb - sa, -sa - sb, cb - ca],
                ]
            )
        else:
            return 0.5 * self._backend.astensor(
                [
                    [cp - ca, -sb, sa - sp, -1 - cb],
                    [-sa - sp, 1 - cb, -ca - cp, sb],
                    [sp - sa, 1 + cb, cp - ca, -sb],
                    [cp + ca, -sb, -sa - sp, 1 - cb],
                ]
            )

    def two_mode_squeezing_symplectic(self, r: Scalar, phi: Scalar) -> Matrix:
        r"""Symplectic matrix of a two-mode squeezing gate.
        The dimension is 4x4.
        Args:
            r (float): squeezing magnitude
            phi (float): rotation parameter
        Returns:
            Matrix: symplectic matrix of a two-mode squeezing gate
        """
        cp = self._backend.cos(phi)
        sp = self._backend.sin(phi)
        ch = self._backend.cosh(r)
        sh = self._backend.sinh(r)
        zero = self._backend.zeros_like(r)
        return self._backend.astensor(
            [
                [ch, cp * sh, zero, sp * sh],
                [cp * sh, ch, sp * sh, zero],
                [zero, sp * sh, ch, -cp * sh],
                [sp * sh, zero, -cp * sh, ch],
            ]
        )

    # ~~~~~~~~~~~~~
    # CPTP channels
    # ~~~~~~~~~~~~~

    def CPTP(self, cov: Matrix, means: Vector, X: Matrix, Y: Matrix, d: Vector, modes: Sequence[int]) -> Tuple[Matrix, Vector]:
        r"""Returns the cov matrix of a state after undergoing a CPTP channel, computed as `cov = X \cdot cov \cdot X^T + Y`.
        If the channel is single-mode, `modes` can contain `M` modes to apply the channel to,
        otherwise it must contain as many modes as the number of modes in the channel.

        Args:
            cov (Matrix): covariance matrix
            means (Vector): means vector
            X (Matrix): the X matrix of the CPTP channel
            Y (Matrix): noise matrix of the CPTP channel
            d (Vector): displacement vector of the CPTP channel
            modes (Sequence[int]): modes on which the channel operates
        Returns:
            Tuple[Matrix, Vector]: the covariance matrix and the means vector of the state after the CPTP channel
        """
        # if single-mode channel, apply to all modes indicated in `modes`
        if X is not None and X.shape[-1] == 2:
            X = self._backend.single_mode_to_multimode_mat(X, len(modes))
        if Y is not None and Y.shape[-1] == 2:
            Y = self._backend.single_mode_to_multimode_mat(Y, len(modes))
        if d is not None and d.shape[-1] == 2:
            d = self._backend.single_mode_to_multimode_vec(d, len(modes))
        cov = self._backend.left_matmul_at_modes(X, cov, modes)
        cov = self._backend.right_matmul_at_modes(cov, self._backend.transpose(X), modes)
        cov = self._backend.add_at_modes(cov, Y, modes)
        means = self._backend.matvec_at_modes(X, means, modes)
        means = self._backend.add_at_modes(means, d, modes)
        return cov, means

    def loss_X(self, transmissivity: Union[Scalar, Vector]) -> Matrix:
        r"""Returns the X matrix for the lossy bosonic channel.
        The full channel is applied to a covariance matrix `\Sigma` as `X\Sigma X^T + Y`.
        """
        D = self._backend.sqrt(transmissivity)
        return self._backend.diag(self._backend.concat([D, D], axis=0))

    def loss_Y(self, transmissivity: Union[Scalar, Vector], hbar: float) -> Matrix:
        r"""Returns the Y (noise) matrix for the lossy bosonic channel.
        The full channel is applied to a covariance matrix `\Sigma` as `X\Sigma X^T + Y`.
        """
        D = (1.0 - transmissivity) * hbar / 2
        return self._backend.diag(self._backend.concat([D, D], axis=0))

    def thermal_X(self, nbar: Union[Scalar, Vector], hbar: float) -> Matrix:
        r"""Returns the X matrix for the thermal lossy channel.
        The full channel is applied to a covariance matrix `\sigma` as `X\sigma X^T + Y`.
        """
        raise NotImplementedError

    def thermal_Y(self, nbar: Union[Scalar, Vector], hbar: float) -> Matrix:
        r"""Returns the Y (noise) matrix for the thermal lossy channel.
        The full channel is applied to a covariance matrix `\sigma` as `X\sigma X^T + Y`.
        """
        raise NotImplementedError

    # ~~~~~~~~~~~~~~~
    # non-TP channels
    # ~~~~~~~~~~~~~~~

    def general_dyne(
        self, cov: Matrix, means: Vector, proj_cov: Matrix, proj_means: Vector, modes: Sequence[int], hbar: float
    ) -> Tuple[Scalar, Matrix, Vector]:
        r"""
        Returns the results of a general dyne measurement.
        Arguments:
            cov (Matrix): covariance matrix of the state being measured
            means (Vector): means vector of the state being measured
            proj_cov (Matrix): covariance matrix of the state being projected onto
            proj_means (Vector): means vector of the state being projected onto (i.e. the measurement outcome)
            modes (Sequence[int]): modes being measured
        Returns:
            Tuple[Scalar, Matrix, Vector]: the outcome probability *density*, the post-measurement cov and means vector
        """
        N = len(cov) // 2
        nB = len(proj_cov) // 2  # B is the system being measured
        nA = N - nB  # A is the system left over after measurement
        Amodes = [i for i in range(N) if i not in modes]
        A, B, AB = self.partition_cov(cov, Amodes)
        a, b = self.partition_means(means, Amodes)
        inv = self._backend.inv(B + proj_cov)
        ABinv = self._backend.matmul(AB, inv)
        new_cov = A - self._backend.matmul(ABinv, self._backend.transpose(AB))
        new_means = a + self._backend.matvec(ABinv, proj_means - b)
        prob = self._backend.exp(-self._backend.sum(self._backend.matvec(inv, proj_means - b) * proj_means - b)) / (
            pi ** nB * (hbar ** -nB) * self._backend.sqrt(self._backend.det(B + proj_cov))
        )  # TODO: check this (hbar part especially)
        return prob, new_cov, new_means

    # ~~~~~~~~~
    # utilities
    # ~~~~~~~~~

    def is_mixed_cov(self, cov: Matrix) -> bool:
        r"""
        Returns True if the covariance matrix is mixed, False otherwise.
        """
        return not is_pure_cov(self._backend.asnumpy(cov))

    def trace(self, cov: Matrix, means: Vector, Bmodes: Sequence[int]) -> Tuple[Matrix, Vector]:
        r"""
        Returns the covariances and means after discarding the specified modes.
        Arguments:
            cov (Matrix): covariance matrix
            means (Vector): means vector
            Bmodes (Sequence[int]): modes to discard
        Returns:
            Tuple[Matrix, Vector]: the covariance matrix and the means vector after discarding the specified modes
        """
        N = len(cov) // 2
        Aindices = self._backend.astensor([i for i in range(N) if i not in Bmodes])
        A_cov_block = self._backend.gather(self._backend.gather(cov, Aindices, axis=0), Aindices, axis=1)
        A_means_vec = self._backend.gather(means, Aindices)
        return A_cov_block, A_means_vec

    def partition_cov(self, cov: Matrix, Amodes: Sequence[int]) -> Tuple[Matrix, Matrix, Matrix]:
        r"""
        Partitions the covariance matrix into the A and B subsystems and the AB coherence block.
        Arguments:
            cov (Matrix): the covariance matrix
            Amodes (Sequence[int]): the modes of system A
        Returns:
            Tuple[Matrix, Matrix, Matrix]: the cov of A, the cov of B and the AB block
        """
        N = cov.shape[-1] // 2
        Bindices = self._backend.cast([i for i in range(N) if i not in Amodes] + [i + N for i in range(N) if i not in Amodes], "int32")
        Aindices = self._backend.cast(Amodes + [i + N for i in Amodes], "int32")
        A_block = self._backend.gather(self._backend.gather(cov, Aindices, axis=1), Aindices, axis=0)
        B_block = self._backend.gather(self._backend.gather(cov, Bindices, axis=1), Bindices, axis=0)
        AB_block = self._backend.gather(self._backend.gather(cov, Bindices, axis=1), Aindices, axis=0)
        return A_block, B_block, AB_block

    def partition_means(self, means: Vector, Amodes: Sequence[int]) -> Tuple[Vector, Vector]:
        r"""
        Partitions the means vector into the A and B subsystems.
        Arguments:
            means (Vector): the means vector
            Amodes (Sequence[int]): the modes of system A
        Returns:
            Tuple[Vector, Vector]: the means of A and the means of B
        """
        N = len(means) // 2
        Bindices = self._backend.cast([i for i in range(N) if i not in Amodes] + [i + N for i in range(N) if i not in Amodes], "int32")
        Aindices = self._backend.cast(Amodes + [i + N for i in Amodes], "int32")
        return self._backend.gather(means, Aindices), self._backend.gather(means, Bindices)

    def purity(self, cov: Matrix, hbar: float) -> Scalar:
        r"""
        Returns the purity of the state with the given covariance matrix.
        Arguments:
            cov (Matrix): the covariance matrix
        Returns:
            float: the purity
        """
        return 1 / self._backend.sqrt(self._backend.det((2 / hbar) * cov))
