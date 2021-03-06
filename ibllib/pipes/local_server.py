import logging
from pathlib import Path

from ibllib.pipes import ephys_preprocessing, training_preprocessing, tasks
import ibllib.io.raw_data_loaders as rawio

import oneibl.registration as registration
from oneibl.one import ONE

_logger = logging.getLogger('ibllib')


def _get_lab(one):
    with open(Path.home().joinpath(".globusonline/lta/client-id.txt"), 'r') as fid:
        globus_id = fid.read()
    lab = one.alyx.rest('labs', 'list', django=f"repositories__globus_endpoint_id,{globus_id}")
    if len(lab):
        return [la['name'] for la in lab]


def job_creator(root_path, one=None, dry=False, rerun=False, max_md5_size=None):
    """
    Server function that will look for creation flags and for each:
    1) create the sessions on Alyx
    2) register the corresponding raw data files on Alyx
    3) create the tasks to be run on Alyx
    :param root_path: main path containing sessions or session path
    :param one
    :param dry
    :param rerun
    :param max_md5_size
    :return:
    """
    if not one:
        one = ONE()
    rc = registration.RegistrationClient(one=one)
    flag_files = list(Path(root_path).glob('**/extract_me.flag'))
    flag_files += list(Path(root_path).glob('**/extract_ephys.flag'))
    all_datasets = []
    for flag_file in flag_files:
        session_path = flag_file.parent
        _logger.info(f'creating session for {session_path}')
        if dry:
            continue
        # providing a false flag stops the registration after session creation
        rc.create_session(session_path)
        flag_file.unlink()
        files, dsets = registration.register_session_raw_data(
            session_path, one=one, max_md5_size=max_md5_size)
        if dsets is not None:
            all_datasets.extend(dsets)
        session_type = rawio.get_session_extractor_type(session_path)
        if session_type in ['biased', 'habituation', 'training']:
            pipe = training_preprocessing.TrainingExtractionPipeline(session_path, one=one)
        elif session_type in ['ephys']:
            pipe = ephys_preprocessing.EphysExtractionPipeline(session_path, one=one)
        else:
            _logger.info(f"Session type {session_type} as no matching extractor {session_path}")
        if rerun:
            rerun__status__in = '__all__'
        else:
            rerun__status__in = ['Waiting']
        pipe.create_alyx_tasks(rerun__status__in=rerun__status__in)
    return all_datasets


def job_runner(subjects_path, lab=None, dry=False, one=None, count=5):
    """
    Function to be used as a process to run the jobs as they are created on the database
    THis will query waiting jobs from the specified Lab
    :param subjects_path: on servers: /mnt/s0/Data/Subjects. Contains sessions
    :param lab: lab name as per Alyx
    :param dry:
    :param count:
    :return:
    """
    if one is None:
        one = ONE()
    if lab is None:
        lab = _get_lab(one)
    if lab is None:
        return  # if the lab is none, this will return empty tasks each time
    tasks = one.alyx.rest('tasks', 'list', status='Waiting',
                          django=f'session__lab__name__in,{lab}')
    tasks_runner(subjects_path, tasks, one=one, count=count, dry=dry)


def tasks_runner(subjects_path, tasks_dict, one=None, dry=False, count=5, **kwargs):
    """
    Function to run a list of tasks (task dictionary from Alyx query) on a local server
    :param subjects_path:
    :param tasks_dict:
    :param one:
    :param dry:
    :param kwargs:
    :return: list of dataset dictionaries
    """
    if one is None:
        one = ONE()

    c = 0
    last_session = None
    all_datasets = []
    for tdict in tasks_dict:
        if c >= count:
            break
        # reconstruct the session local path. As many jobs belong to the same session
        # cache the result
        if last_session != tdict['session']:
            ses = one.alyx.rest('sessions', 'list', django=f"pk,{tdict['session']}")[0]
            session_path = Path(subjects_path).joinpath(
                Path(ses['subject'], ses['start_time'][:10], str(ses['number']).zfill(3)))
            last_session = tdict['session']
        if dry:
            print(session_path, tdict['name'])
        else:
            task, dsets = tasks.run_alyx_task(tdict=tdict, session_path=session_path,
                                              one=one, **kwargs)
            if dsets:
                all_datasets.extend(dsets)
                c += 1
    return all_datasets
