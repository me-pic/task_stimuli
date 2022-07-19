import os

def get_tasks(parsed):
    from ..tasks import language, task_base
    from psychopy import logging
    bids_sub = "sub-%s" % parsed.subject
    savestate_path = os.path.abspath(os.path.join(parsed.output, "sourcedata", bids_sub, f"{bids_sub}_task-triplet_savestate.json"))

    # check for a "savestate"
    if os.path.exists(savestate_path):
        with open(savestate_path) as f:
            savestate = json.load(f)
    else:
        savestate = {"session": 1}
    logging.exp(f"loading savestate: currently on session {savestate['session']:03d}")

    #only one run of each
    run = 1

    yield language.WordFamiliarity(
        f"{TRIPLET_DATA_PATH}/words_designs/sub-{parsed.subject}_ses-{savestate['session']:03d}_run-{run:02d}_design.tsv",
        name="task-singlewords",
        use_eyetracking=True,
    )
    yield task_base.Pause(
        text="You can take a short break.\n Press A when ready to continue",
        wait_key='a',
    )

    yield language.Triplet(
        f"{TRIPLET_DATA_PATH}/designs/sub-{parsed.subject}_ses-{savestate['session']:03d}_run-{run:02d}_design.tsv",
        name="task-triplets",
        use_eyetracking=True,
    )

    savestate['session'] += 1
    logging.exp(f"saving savestate: next session {savestate['session']:03d}")
    with open(savestate_path, 'w') as f:
        json.dump(savestate, f)

    return TASKS

TRIPLET_DATA_PATH = "data/language/triplets"
TR=1.49
N_TRIALS_PER_RUN = 59 # 708/59=12
N_RUNS_PER_SESSION = 1
STIMULI_DURATION = 4
TRIAL_DURATION = 4*TR
BASELINE_BEGIN = 6
BASELINE_END = 9
ISI = TRIAL_DURATION - STIMULI_DURATION
ISI_JITTER = 2

def generate_design_file(subject, all_triplets, pilot=False):
    import os
    import hashlib
    import numpy as np

    # sample all ISI with same seed for matching run length
    np.random.seed(0)
    isi_set = np.random.random_sample(N_TRIALS_PER_RUN)*ISI_JITTER + ISI

    # seed numpy with subject id to have reproducible design generation
    seed = int(
        hashlib.sha1(("%s" % (subject)).encode("utf-8")).hexdigest(), 16
    ) % (2 ** 32 - 1)
    print("seed", seed)
    np.random.seed(seed)

    # permute categories per participant

    all_triplets = all_triplets.sample(frac=1)
    for run in range(int(np.ceil(len(all_triplets)/N_TRIALS_PER_RUN))):
        run_triplets = all_triplets[run*N_TRIALS_PER_RUN:(run+1)*N_TRIALS_PER_RUN]
        run_triplets['isi'] = np.random.permutation(isi_set)[:len(run_triplets)]
        run_triplets['onset'] = (BASELINE_BEGIN + \
            np.arange(len(run_triplets))*STIMULI_DURATION +
            np.hstack([[0],np.cumsum(run_triplets['isi'][:-1])]))
        run_triplets['duration'] = STIMULI_DURATION

        session = run // N_RUNS_PER_SESSION + 1
        run_in_session = run % N_RUNS_PER_SESSION + 1

        out_fname = os.path.join(
            TRIPLET_DATA_PATH,
            "designs",
            f"sub-{parsed.subject}_ses-{'pilot' if pilot else ''}{session:03d}_run-{run_in_session:02d}_design.tsv",
        )
        print(f"writing {out_fname}")
        run_triplets.to_csv(out_fname, sep="\t", index=False)


if __name__ == "__main__":
    import argparse
    import sys, os
    import pandas

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="generate design files for participant / session",
    )
    parser.add_argument("subject", type=str, help="participant id")
    parser.add_argument(
        "--pilot", help="Use pilot set", action="store_true"
    )

    parsed = parser.parse_args()
    if parsed.pilot:
        all_triplets = pandas.read_csv(os.path.join(TRIPLET_DATA_PATH, 'pilotable_triplets_v2.csv'))
        all_triplets = pandas.DataFrame({
            'target': all_triplets.target,
            'choice_1': all_triplets.candidate_1,
            'choice_2': all_triplets.candidate_2,
        })
    else:
        all_triplets = pandas.read_csv(os.path.join(TRIPLET_DATA_PATH, 'fMRI_triplets.csv'))
    generate_design_file(parsed.subject, all_triplets, parsed.pilot)
