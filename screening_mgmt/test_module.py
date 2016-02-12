""" Test module for the script 'screening_mgmt'.
Last updated 08.02.2016 Andreas Helfenstein
"""

import screening_mgmt as sm
reload(sm)

def test_connect():
    db = sm.DbConnection('sqlite', '','','','')
    assert db.connect()

def test__initialization():
    db = sm.DbConnection('sqlite', '','','','')
    db._initialize()
    db.metadata.reflect(db.engine)
    db_keys = db.metadata.tables.keys()
    assert db_keys[0] == "routines"
    assert db_keys[1] == "results"
    assert db_keys[2] == "users"
    assert db_keys[3] == "compounds"

def test_new_entry():
    db = sm.DbConnection('sqlite', '','','','')
    db._initialize()
    data = {'usr_name':'testname'}
    db.new_entry(sm.Usr, data)
    user_name = db.session.query(sm.Usr.usr_name,).all()
    assert user_name[0][0] == 'testname'
