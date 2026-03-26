import fin_db as fdb


fdb.open_session(user='fin_db_read', host='minicomp')


# Try get_iid
def test_get_iid_mapping_yahoo():
    expected_id = {
        'AAPL': 'EQUAAPLUS0378331005X',
        'MSFT': 'EQUMSFTUS5949181045X',
        'madeup': None
    }
    ids = fdb.queries.get_iid_mapping(
        tickers=['AAPL', 'MSFT', 'madeup'],
        source='YAHOO'
    )
    assert ids['AAPL'] == expected_id['AAPL']
    assert ids['MSFT'] == expected_id['MSFT']
    assert ids['madeup'] == expected_id['madeup']
