if __name__ == '__main__':
    import json
    import time
    from client import SearchClient
    sc = SearchClient('../conf')

    # 1. Lexical query.
    query1 = {'ana.lex': 'vbcvqr'}
    query1 = sc.make_word_ana_query(query1)
    print('query1 (words):', json.dumps(query1, ensure_ascii=False))
    hits = sc.get_words(query1)
    print('Results of query1:')
    print(json.dumps(hits, ensure_ascii=False, indent=1))

    # 2. Grammar query.
    query2 = {'ana.gr.tense': 't7', 'ana.gr.pers': '2'}
    query2 = sc.make_word_ana_query(query2)
    print('query2 (words):', json.dumps(query2, ensure_ascii=False))
    hits = sc.get_words(query2)
    print('Results of query2:')
    print(json.dumps(hits, ensure_ascii=False, indent=1))

    # 3. Grammar query in sentences:
    query2 = {'ana.gr.tense': 't7', 'ana.gr.pers': '2'}
    query2 = sc.make_sent_ana_query(query2)
    print('query2 (sentences):', json.dumps(query2, ensure_ascii=False))
    hits = sc.get_sentences(query2)
    print('Results of query2:')
    print('Hits:', hits['hits']['total'], ', took: ', hits['took'], 'ms.')
