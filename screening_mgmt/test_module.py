""" Test module for the script 'screening_mgmt'.
Last updated 08.02.2016 Andreas Helfenstein
"""

import screening_mgmt as sm
import aux_func as af
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
    
# Testing auxiliary functions

def test_sm_shorten_name():
    name_pairs = (
        ('Escherichia coli','E. coli'),
        ('Escherichia','Escherichia'),
        ('escherichia Coli','E. coli'),
        )
    for pair in name_pairs:
        assert af.sm_shorten_name(pair[0]) == pair[1]

def test_sm_quality():
    vals = af.sm_quality(1,0.1,0.1,0.1)
    assert vals['S2B'] == 10
    assert 6.3 < vals['S2N'] <6.4
    assert 0.33 < vals['Z'] < 0.34
    
def test_Cpd():
    cpd = sm.Cpd(None)
    assert cpd.__tablename__ == "compounds"
    
def test_Usr():
    usr = sm.Usr(None)
    assert usr.__tablename__ == "users"
    
def test_Res():
    res = sm.Res(None)
    assert res.__tablename__ == "results"

if __name__ == "__main__":
    test_Cpd()
