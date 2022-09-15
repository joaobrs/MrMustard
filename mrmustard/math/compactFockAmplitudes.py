import numpy as np
from numba import njit, typeof, int64
from numba.typed import Dict
from scipy.special import binom
from numba.cpython.unsafe.tuple import tuple_setitem

@njit
def len_lvl(M, N, BINOM):
    r"""Returns the size of an M-mode level with N total photons.
    Args:
        M (int) number of modes
        N (int) number of photons in level
    Returns:
        (int) the the size of an M-mode level with N total photons
    """
    return BINOM[M-1+N, N]


@njit
def get_partitions(M, N, PARTITIONS, BINOM):
    r"""Returns an array of partitions (spreading N photons over M modes)
    If the partitions are already computed it returns them from the PARTITIONS dictionary,
    otherwise it fills the PARTITIONS[(M,N)] dictionary entry.
    Args:
        M (int) number of modes
        N (int) number of photons in level
        PARTITIONS (dict) a reference to the "global" PARTITIONS dictionary
    Returns:
        (2d array) the array of pivots for the given level
    """
    if (M,N) in PARTITIONS:
        return PARTITIONS[(M,N)]
    # recursive formulation:
    # (doesn't matter if it's slowish because we're caching the results)
    if M == 1:
        return np.array([[N]])
    else:
        T = 0
        pivots = np.zeros((len_lvl(M, N, BINOM), M), dtype=np.int64)
        for n in range(N+1):
            pivots[T : T + len_lvl(M-1, N-n, BINOM), :1] = n
            pivots[T : T + len_lvl(M-1, N-n, BINOM), 1:] = get_partitions(M-1, N-n, PARTITIONS, BINOM)
            T += len_lvl(M-1, N-n, BINOM)
        PARTITIONS[(M,N)] = pivots
        return pivots


# helper functions to construct tuples that are used for multidimensional indexing of the submatrices of G
@njit
def fill_tuple_tail_Array0(tup, params, M):
    '''
    This function is equivalent to:
        tup = list(tup)
        tup[2:] = params
        return tuple(tup)
    while being compatible with Numba.
    '''
    for t in range(2, M + 2):
        tup = tuple_setitem(tup, t, params[t - 2])
    return tup


@njit
def fill_tuple_tail_Array2(tup, idx0, params, M):
    '''
    This function is equivalent to:
        tup = list(tup)
        tup[3:] = [x for x in range(M) if x!=idx0]
        return tuple(tup)
    while being compatible with Numba.
    '''
    for x in range(M):
        if x < idx0:
            tup = tuple_setitem(tup, x + 3, params[x])
        elif x > idx0:
            tup = tuple_setitem(tup, x + 2, params[x])
    return tup


@njit
def fill_tuple_tail_Array11(tup, idx0, idx1, params, M):
    '''
    This function is equivalent to:
        tup = list(tup)
        tup[4:] = [x for x in range(M) if (x!=idx0 and x!=idx1)]
        return tuple(tup)
    while being compatible with Numba.

    Assumption: idx0<idx1 (i.e. here: [idx0,idx1] == sorted([i,d]))
    '''
    for x in range(M):
        if x < idx0:
            tup = tuple_setitem(tup, x + 4, params[x])
        elif idx0 < x and x < idx1:
            tup = tuple_setitem(tup, x + 3, params[x])
        elif idx1 < x:
            tup = tuple_setitem(tup, x + 2, params[x])
    return tup


# Other helper functions
@njit
def calc_diag_pivot(params):
    '''
    return pivot in original representation of G
    i.e. a,a,b,b,c,c,...
    params [1D array]: [a,b,c,...]
    '''
    pivot = np.zeros(2 * params.shape[0], dtype=np.int64)
    for i, val in enumerate(params):
        pivot[2 * i] = val
        pivot[2 * i + 1] = val
    return pivot


@njit
def calc_offDiag_pivot(params, d):
    '''
    return pivot in original representation of G
    i.e. d=0: a+1,a,b,b,c,c,... | d=1: a,a,b+1,b,c,c,...
    params [1D array]: [a,b,c,...]
    d [int]: index of pivot-offDiagonal
    '''
    pivot = np.zeros(2 * params.shape[0], dtype=np.int64)
    for i, val in enumerate(params):
        pivot[2 * i] = val
        pivot[2 * i + 1] = val
    pivot[2 * d] += 1
    return pivot


@njit
def index_above_diagonal(idx0, idx1, M):  # should memoize these functions
    '''
    Given the indices of an element that is located above the diagonal in an array of shape MxM,
    return a single index that identifies such an element in the following way:
    (Example for M=3)
    [[x,0,1]
     [x,x,2]
     [x,x,x]]
    idx0,idx1=0,1 --> return 0
    idx0,idx1=0,2 --> return 1
    idx0,idx1=1,2 --> return 2
    (Assumption: idx0<idx1)
    '''
    ids = np.cumsum(np.hstack((np.zeros(1, dtype=np.int64), np.arange(2, M, dtype=np.int64)[
                                                            ::-1])))  # desired n for values next to diagonal (e.g. for M=3: ids=[0,2])
    return ids[idx0] + idx1 - idx0 - 1


@njit
def calc_staggered_range_2M(M):
    '''
    Output: np.array([1,0,3,2,5,4,...,2*M-1,2*M-2])
    This array is used to index the fock amplitudes that are read when using a diagonal pivot (i.e. a pivot of type aa,bb,cc,dd,...).
    '''
    A = np.zeros(2 * M, dtype=np.int64)
    for i in range(1, 2 * M, 2):
        A[i - 1] = i
    for i in range(0, 2 * M, 2):
        A[i + 1] = i
    return A


@njit
def calc_dA_dB(i, GB_dA, GB_dB, G_in_dA, G_in_dB, G_in, A, B, read_GB, K_l, K_i, pivot, M, pivot_val):
    dA = GB_dA[i]  # dA = np.zeros(A.shape,dtype=np.complex128) if no displacement
    dB = GB_dB[i]
    dB[i] += pivot_val
    for l in range(2 * M):
        dA += A[i, l] * G_in_dA[l]
        dB += A[i, l] * G_in_dB[l]
        dA[i, l] += G_in[l]
    return dA / K_i[i], dB / K_i[i]


@njit
def use_offDiag_pivot(A, B, M, cutoff, params, d, arr0, arr2, arr11, arr1, zero_tuple, arr0_dA, arr2_dA, arr11_dA,
                      arr1_dA, arr0_dB, arr2_dB, arr11_dB, arr1_dB):
    pivot = calc_offDiag_pivot(params, d)
    K_l = np.sqrt(pivot)  # automatic conversion to float
    K_i = np.sqrt(pivot + 1)  # automatic conversion to float
    G_in = np.zeros(2 * M, dtype=np.complex128)
    G_in_dA = np.zeros((2 * M,) + A.shape, dtype=np.complex128)
    G_in_dB = np.zeros((2 * M,) + B.shape, dtype=np.complex128)

    read_GB = tuple_setitem(zero_tuple, 1, 2 * d)
    read_GB = tuple_setitem(read_GB, 2, params[d])
    read_GB = fill_tuple_tail_Array2(read_GB, d, params, M)
    pivot_val = arr1[read_GB]
    GB = arr1[read_GB] * B
    GB_dA = np.zeros(B.shape + A.shape, dtype=np.complex128)
    GB_dB = np.zeros(B.shape + B.shape, dtype=np.complex128)
    for idx in range(len(B)):
        GB_dA[idx] = arr1_dA[read_GB] * B[idx]
        GB_dB[idx] = arr1_dB[read_GB] * B[idx]

    ########## READ ##########

    # Array0
    read0 = fill_tuple_tail_Array0(zero_tuple, params,
                                   M)  # can store this one as I do not need to check boundary conditions for Array0! (Doesn't work for other arrays)
    G_in[2 * d] = arr0[read0]
    G_in_dA[2 * d] = arr0_dA[read0]
    G_in_dB[2 * d] = arr0_dB[read0]

    # read from Array2
    if params[d] > 0:  # params[d]-1>=0
        read = zero_tuple
        read = tuple_setitem(read, 1, d)
        read = tuple_setitem(read, 2, params[d] - 1)
        read = fill_tuple_tail_Array2(read, d, params, M)
        G_in[2 * d + 1] = arr2[read]
        G_in_dA[2 * d + 1] = arr2_dA[read]
        G_in_dB[2 * d + 1] = arr2_dB[read]

    # read from Array11
    for i in range(d + 1, M):  # i>d
        if params[i] > 0:
            read = zero_tuple
            read = tuple_setitem(read, 1, index_above_diagonal(d, i, M))
            read = tuple_setitem(read, 2, params[d])
            read = tuple_setitem(read, 3, params[i] - 1)
            read = fill_tuple_tail_Array11(read, d, i, params, M)
            G_in[2 * i] = arr11[tuple_setitem(read, 0, 1)]  # READ green (1001)
            G_in_dA[2 * i] = arr11_dA[tuple_setitem(read, 0, 1)]
            G_in_dB[2 * i] = arr11_dB[tuple_setitem(read, 0, 1)]
            G_in[2 * i + 1] = arr11[read]  # READ red (1010)
            G_in_dA[2 * i + 1] = arr11_dA[read]
            G_in_dB[2 * i + 1] = arr11_dB[read]

    for i in range(d):  # i<d
        if params[i] > 0:
            read = zero_tuple
            read = tuple_setitem(read, 1, index_above_diagonal(i, d, M))
            read = tuple_setitem(read, 2, params[i] - 1)
            read = tuple_setitem(read, 3, params[d])
            read = fill_tuple_tail_Array11(read, i, d, params, M)

            G_in[2 * i] = arr11[tuple_setitem(read, 0, 2)]  # READ blue (0110)
            G_in_dA[2 * i] = arr11_dA[tuple_setitem(read, 0, 2)]
            G_in_dB[2 * i] = arr11_dB[tuple_setitem(read, 0, 2)]

            G_in[2 * i + 1] = arr11[read]  # READ red (1010)
            G_in_dA[2 * i + 1] = arr11_dA[read]
            G_in_dB[2 * i + 1] = arr11_dB[read]

    ########## WRITE ##########

    G_in = np.multiply(K_l, G_in)
    for idx in range(len(K_l)):
        G_in_dA[idx] *= K_l[idx]
    for idx in range(len(K_l)):
        G_in_dB[idx] *= K_l[idx]

    # Array0
    if d == 0 or np.all(params[:d] == 0):
        write0 = tuple_setitem(read0, 2 + d, params[d] + 1)
        arr0[write0] = (GB[2 * d + 1] + A[2 * d + 1] @ G_in) / K_i[2 * d + 1]  # I could absorb K_i in A and GB
        arr0_dA[write0], arr0_dB[write0] = calc_dA_dB(2 * d + 1, GB_dA, GB_dB, G_in_dA, G_in_dB, G_in, A, B, read_GB,
                                                      K_l, K_i, pivot, M, pivot_val)

    # Array2
    if params[d] + 2 < cutoff:
        write = zero_tuple
        write = tuple_setitem(write, 1, d)
        write = tuple_setitem(write, 2, params[d])
        write = fill_tuple_tail_Array2(write, d, params, M)
        arr2[write] = (GB[2 * d] + A[2 * d] @ G_in) / K_i[2 * d]
        arr2_dA[write], arr2_dB[write] = calc_dA_dB(2 * d, GB_dA, GB_dB, G_in_dA, G_in_dB, G_in, A, B, read_GB, K_l,
                                                    K_i, pivot, M, pivot_val)

    # Array11
    for i in range(d + 1, M):
        if params[i] + 1 < cutoff:
            write = zero_tuple
            write = tuple_setitem(write, 1, index_above_diagonal(d, i, M))
            write = tuple_setitem(write, 2, params[d])
            write = tuple_setitem(write, 3, params[i])
            write = fill_tuple_tail_Array11(write, d, i, params, M)

            arr11[write] = (GB[2 * i] + A[2 * i] @ G_in) / K_i[2 * i]  # WRITE red (1010)
            arr11_dA[write], arr11_dB[write] = calc_dA_dB(2 * i, GB_dA, GB_dB, G_in_dA, G_in_dB, G_in, A, B, read_GB,
                                                          K_l, K_i, pivot, M, pivot_val)

            arr11[tuple_setitem(write, 0, 1)] = (GB[2 * i + 1] + A[2 * i + 1] @ G_in) / K_i[
                2 * i + 1]  # WRITE green (1001)
            arr11_dA[tuple_setitem(write, 0, 1)], arr11_dB[tuple_setitem(write, 0, 1)] = calc_dA_dB(2 * i + 1, GB_dA,
                                                                                                    GB_dB, G_in_dA,
                                                                                                    G_in_dB, G_in, A, B,
                                                                                                    read_GB, K_l, K_i,
                                                                                                    pivot, M, pivot_val)

    for i in range(d):
        if params[i] + 1 < cutoff:
            write = zero_tuple
            write = tuple_setitem(write, 1, index_above_diagonal(i, d, M))
            write = tuple_setitem(write, 2, params[i])
            write = tuple_setitem(write, 3, params[d])
            write = fill_tuple_tail_Array11(write, i, d, params, M)
            arr11[tuple_setitem(write, 0, 2)] = (GB[2 * i + 1] + A[2 * i + 1] @ G_in) / K_i[
                2 * i + 1]  # WRITE blue (0110)
            arr11_dA[tuple_setitem(write, 0, 2)], arr11_dB[tuple_setitem(write, 0, 2)] = calc_dA_dB(2 * i + 1, GB_dA,
                                                                                                    GB_dB, G_in_dA,
                                                                                                    G_in_dB, G_in, A, B,
                                                                                                    read_GB, K_l, K_i,
                                                                                                    pivot, M, pivot_val)

    return arr0, arr2, arr11, arr1, arr0_dA, arr2_dA, arr11_dA, arr1_dA, arr0_dB, arr2_dB, arr11_dB, arr1_dB


@njit
def use_diag_pivot(A, B, M, cutoff, params, arr0, arr1, zero_tuple, staggered_range, arr0_dA, arr1_dA, arr0_dB,
                   arr1_dB):
    pivot = calc_diag_pivot(params)
    K_l = np.sqrt(pivot)  # automatic conversion to float
    K_i = np.sqrt(pivot + 1)  # automatic conversion to float
    G_in = np.zeros(2 * M, dtype=np.complex128)
    G_in_dA = np.zeros((2 * M,) + A.shape, dtype=np.complex128)
    G_in_dB = np.zeros((2 * M,) + B.shape, dtype=np.complex128)

    read_GB = fill_tuple_tail_Array0(zero_tuple, params, M)
    pivot_val = arr0[read_GB]
    GB = arr0[read_GB] * B
    GB_dA = np.zeros(B.shape + A.shape, dtype=np.complex128)
    GB_dB = np.zeros(B.shape + B.shape, dtype=np.complex128)
    for idx in range(len(B)):
        GB_dA[idx] = arr0_dA[read_GB] * B[idx]
        GB_dB[idx] = arr0_dB[read_GB] * B[idx]

    ########## READ ##########
    # Array1
    for i in range(2 * M):
        if params[i // 2] > 0:
            read = zero_tuple
            read = tuple_setitem(read, 1, staggered_range[i])
            read = tuple_setitem(read, 2, params[i // 2] - 1)
            read = fill_tuple_tail_Array2(read, i // 2, params, M)
            G_in[i] = arr1[read]
            G_in_dA[i] = arr1_dA[read]
            G_in_dB[i] = arr1_dB[read]

    ########## WRITE ##########
    G_in = np.multiply(K_l, G_in)
    for idx in range(len(K_l)):
        G_in_dA[idx] *= K_l[idx]
    for idx in range(len(K_l)):
        G_in_dB[idx] *= K_l[idx]

    # Array1
    for i in range(2 * M):
        if params[i // 2] + 1 < cutoff:
            write = tuple_setitem(zero_tuple, 1, i)
            write = tuple_setitem(write, 2, params[i // 2])
            write = fill_tuple_tail_Array2(write, i // 2, params, M)
            arr1[write] = (GB[i] + A[i] @ G_in) / K_i[i]
            arr1_dA[write], arr1_dB[write] = calc_dA_dB(i, GB_dA, GB_dB, G_in_dA, G_in_dB, G_in, A, B, read_GB, K_l,
                                                        K_i, pivot, M, pivot_val)
    return arr0, arr1, arr0_dA, arr1_dA, arr0_dB, arr1_dB


@njit
def fock_representation_compact_NUMBA(A, B, G0, M, cutoff, PARTITIONS, BINOM, arr0, arr2, arr11, arr1, zero_tuple):
    '''
    Returns the PNR probabilities of a state or Choi state (by using the recurrence relation to calculate a limited number of Fock amplitudes)
    Args:
        A, B, G0 (Matrix, Vector, Scalar): ABC that are used to apply the recurrence relation
        M (int): number of modes
        cutoff (int): upper bound for the number of photons in each mode
        PARTITIONS (dict): a reference to the "global" PARTITIONS dictionary that is used to iterate over all pivots
        arr0 (Matrix): submatrix of the fock representation that contains Fock amplitudes of the type aa,bb,...
        arr2 (Matrix): submatrix of the fock representation that contains Fock amplitudes of the types (a+2)a,bb,... / aa,(b+2)b,... / ...
        arr11 (Matrix): submatrix of the fock representation that contains Fock amplitudes of the types (a+1)a,(b+1)b,... / (a+1)a,b(b+1),... / a(a+1),(b+1)b,...
        arr1 (Matrix): submatrix of the fock representation that contains Fock amplitudes of the types (a+1)a,bb,... / a(a+1),bb,... / aa,(b+1)b,... / ...
        zero_tuple (tuple): tuple of length M+3 containing integer zeros
    Returns:
        Tensor: the fock representation
    '''
    arr0_dA = np.zeros(arr0.shape + A.shape, dtype=np.complex128)
    arr2_dA = np.zeros(arr2.shape + A.shape, dtype=np.complex128)
    arr11_dA = np.zeros(arr11.shape + A.shape, dtype=np.complex128)
    arr1_dA = np.zeros(arr1.shape + A.shape, dtype=np.complex128)
    arr0_dB = np.zeros(arr0.shape + B.shape, dtype=np.complex128)
    arr2_dB = np.zeros(arr2.shape + B.shape, dtype=np.complex128)
    arr11_dB = np.zeros(arr11.shape + B.shape, dtype=np.complex128)
    arr1_dB = np.zeros(arr1.shape + B.shape, dtype=np.complex128)

    arr0[zero_tuple] = G0
    staggered_range = calc_staggered_range_2M(M)
    for count in range((cutoff - 1) * M):  # count = (sum_weight(pivot)-1)/2 # Note: sum_weight(pivot) = 2*(a+b+c+...)+1
        for params in get_partitions(M, count, PARTITIONS, BINOM):
            if np.max(params) < cutoff:
                # diagonal pivots: aa,bb,cc,dd,...
                arr0, arr1, arr0_dA, arr1_dA, arr0_dB, arr1_dB = use_diag_pivot(A, B, M, cutoff, params, arr0, arr1,
                                                                                zero_tuple, staggered_range, arr0_dA,
                                                                                arr1_dA, arr0_dB, arr1_dB)

                # off-diagonal pivots: d=0: (a+1)a,bb,cc,dd,... | d=1: aa,(b+1)b,cc,dd | ...
                for d in range(M):  # for over pivot off-diagonals
                    if params[d] < cutoff - 1:
                        arr0, arr2, arr11, arr1, arr0_dA, arr2_dA, arr11_dA, arr1_dA, arr0_dB, arr2_dB, arr11_dB, arr1_dB = use_offDiag_pivot(
                            A, B, M, cutoff, params, d, arr0, arr2, arr11, arr1, zero_tuple, arr0_dA, arr2_dA, arr11_dA,
                            arr1_dA, arr0_dB, arr2_dB, arr11_dB, arr1_dB)

    return arr0[0, 0], arr0_dA[0, 0], arr0_dB[0, 0]


def fock_representation_compact(A, B, G0, M, cutoff):
    '''
    First initialise the submatrices of G (of which the shape depends on cutoff and M)
    and initialise a zero tuple of length M+2.
    (These initialisations currently cannot be done using Numba.)
    Then calculate the fock representation.
    '''
    BINOM = np.zeros((60, 60), dtype=np.int64)
    for m in range(BINOM.shape[0]):
        for n in range(BINOM.shape[1]):
            BINOM[m, n] = binom(m, n)
    PARTITIONS = Dict.empty(key_type=typeof((0, 0)), value_type=int64[:, :])
    arr0 = np.zeros([1, 1] + [cutoff] * M, dtype=np.complex128)
    arr2 = np.zeros([1, M] + [cutoff - 2] + [cutoff] * (M - 1), dtype=np.complex128)
    if M == 1:
        arr11 = np.zeros([1, 1, 1],
                         dtype=np.complex128)  # we will never read from/write to arr11 for M=1, but Numba requires it to have correct dimensions(corresponding to the length of tuples that are used for multidim indexing, i.e. M+2)
    else:
        arr11 = np.zeros([3] + [M * (M - 1) // 2] + [cutoff - 1] * 2 + [cutoff] * (M - 2), dtype=np.complex128)
    arr1 = np.zeros([1, 2 * M] + [cutoff - 1] + [cutoff] * (M - 1), dtype=np.complex128)
    zero_tuple = tuple([0] * (M + 2))
    return fock_representation_compact_NUMBA(A, B, G0, M, cutoff, PARTITIONS, BINOM, arr0, arr2, arr11, arr1, zero_tuple)



# def fock_representation_compact(A,B,G,G_dA,G_dB):
#     PARTITIONS = Dict.empty(key_type=typeof((0, 0)), value_type=int64[:, :])
#     M = A.shape[0]//2
#     cutoff = G.shape[0]
#
#     for count in range((cutoff-1)*M): # count = (sum_weight(pivot)-1)/2 # Note: sum_weight(pivot) = 2*(a+b+c+...)+1
#         for params in get_partitions(M, count, PARTITIONS):
#             if np.max(params)<cutoff:
#                 # diagonal pivots: aa,bb,cc,dd,...
#                 # G,G_dA = use_diag_pivot(A,B,M,cutoff,params,G,G_dA)
#
#                 # off-diagonal pivots: d=0: (a+1)a,bb,cc,dd,... | d=1: aa,(b+1)b,cc,dd | ...
#                 for d in range(M): # for over pivot off-diagonals
#                     if params[d]<cutoff-1:
#                         G,G_dA = use_offDiag_pivot(A,B,M,cutoff,params,d,G,G_dA)
#     return G,G_dA,G_dB
#
def hermite_multidimensional_diagonal(A,B,G0,cutoff):
    M = A.shape[0]//2
    # G = np.zeros([cutoff]*(2*M),dtype=np.complex128)
    # G[tuple([0] * (2 * M))] = G0
    # G_dA = np.zeros(G.shape + A.shape, dtype=np.complex128)
    # G_dB = np.zeros(G.shape + B.shape, dtype=np.complex128)
    G,G_dA,G_dB = fock_representation_compact(A, B, G0, M, cutoff)
    G_dG0 = np.array(G / G0).astype(np.complex128)
    return G,G_dG0,G_dA,G_dB