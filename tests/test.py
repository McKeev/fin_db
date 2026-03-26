import fin_db as fdb


fdb.open_session(user='fin_db_read', host='minicomp')


# Try get_iid
def test_get_iid_mapping_yahoo():
    expected_id = {
        'AAPL': 'EQUAAPLUS0378331005X',
        'MSFT': 'EQUMSFTUS5949181045X',
    }
    ids = fdb.queries.get_iid_mapping(
        tickers=['AAPL', 'MSFT'],
        source='YAHOO'
    )
    assert ids['AAPL'] == expected_id['AAPL']
    assert ids['MSFT'] == expected_id['MSFT']
