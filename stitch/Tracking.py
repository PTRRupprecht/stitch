import numpy as np
import scipy.spatial.distance as ssd


def track_positions(positions, new_trajectory_cost, cutoff):
    n_steps = len(positions) - 1
    matches = [
        match(positions[i],
              positions[i + 1],
              new_trajectory_cost=new_trajectory_cost,
              cutoff=cutoff) for i in range(n_steps)
    ]
    n_pre = len(positions[0])
    trajectories = [[(0, i)] for i in range(n_pre)]
    active = [i for i in range(n_pre)]
    for t in range(1, n_steps + 1):
        n_post = len(positions[t])
        pre = [trajectories[a][-1][1] for a in active]
        m = matches[t - 1]
        post = [m[p] for p in pre]
        p_post = []
        p_end = []
        for a, p in enumerate(post):
            if p == n_post:
                p_end.append(a)
            else:
                trajectories[active[a]].append((t, p))
                p_post.append(p)
        for i in sorted(p_end, reverse=True):
            del active[i]
        new = np.setdiff1d(range(n_post), p_post)
        for p in new:
            active.append(len(trajectories))
            trajectories.append([(t, p)])
    return trajectories


def match(positions_pre, positions_post, new_trajectory_cost, cutoff):
    cost = ssd.cdist(positions_pre, positions_post)
    if cutoff:
        cost[cost > cutoff] = np.inf
    if new_trajectory_cost is None:
        new_trajectory_cost = np.max(cost) + 1.0
    cost = np.pad(cost, [(0, 1), (0, 1)],
                  'constant',
                  constant_values=new_trajectory_cost)
    A = optimal_association_matrix(cost)
    return {i: j for i, j in zip(*np.where(A[:-1, :]))}


def optimal_association_matrix(cost):
    A = _init_association_matrix(cost)
    Cs = np.where(cost[:-1, :-1].flatten() < np.inf)
    finished = False
    while not finished:
        A, finished = _do_one_move(A, cost, Cs)
    return A


def _init_association_matrix(cost):
    osize = cost.shape[0] - 1
    nsize = cost.shape[1] - 1
    A = np.zeros((osize + 1, nsize + 1), dtype=bool)
    for i in range(osize):
        srtidx = np.argsort(cost[i, :])
        dumidx = np.where(srtidx == nsize)[0]
        iidx = 0
        while np.sum(A[:, srtidx[iidx]]) != 0 and iidx < dumidx:
            iidx = iidx + 1
        A[i, srtidx[iidx]] = True
    s = np.sum(A, axis=0)
    A[osize, s < 1] = True
    A[osize, nsize] = True
    return A


def _do_one_move(A, C, Cs):
    osize = A.shape[0] - 1
    nsize = A.shape[1] - 1
    todo = np.intersect1d(
        np.where(np.logical_not(A[:osize, :nsize].flatten()))[0], Cs)
    if len(todo) == 0:
        return A, True
    iCand, jCand = np.unravel_index(todo, (osize, nsize))
    yCand = [np.where(A[ic, :])[0][0] for ic in iCand]
    xCand = [np.where(A[:, jc])[0][0] for jc in jCand]
    cRed = [
        C[i, j] + C[x, y] - C[i, y] - C[x, j]
        for i, j, x, y in zip(iCand, jCand, xCand, yCand)
    ]
    rMin = np.argmin(cRed)
    rCost = cRed[rMin]
    if rCost < -1e-10:
        A[iCand[rMin], jCand[rMin]] = 1
        A[xCand[rMin], jCand[rMin]] = 0
        A[iCand[rMin], yCand[rMin]] = 0
        A[xCand[rMin], yCand[rMin]] = 1
        finished = False
    else:
        finished = True
    return A, finished
