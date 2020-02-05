import os
import re
import html
import json
import copy
from txt2json import Txt2JSON


class SocialNetworks2JSON(Txt2JSON):
    """
    Contains methods to make JSONs ready for indexing from
    social network JSONs preliminary split into sentences and
    tagged by language, and a list with analyzed word forms
    for each language.
    """

    allowedMetaKeys = {'account_type', 'sex', 'byear', 'home_town', 'city', 'author_id'}

    def __init__(self, settingsDir='conf_conversion'):
        Txt2JSON.__init__(self, settingsDir=settingsDir)
        self.srcExt = 'json'
        self.glosses = set()

    def get_post_sentences(self, postSentences, authorMeta, defaultMeta, postType, year=None):
        """
        Take a source list of sentences of a single post or comment and process them.
        """
        processedSentences = []
        curMeta = {'post_type': postType}
        if type(authorMeta) != dict:
            authorMeta = defaultMeta
        for k in authorMeta:
            if k in self.allowedMetaKeys:
                curMeta[k + '_post'] = authorMeta[k]
        if type(year) == int:
            curMeta['year_post'] = year
        for s in postSentences:
            sProcessed = copy.deepcopy(s)
            sProcessed['meta'] = copy.deepcopy(curMeta)
            processedSentences.append(sProcessed)
        if len(processedSentences) > 0 and not processedSentences[-1]['text'].endswith('\n'):
            processedSentences[-1]['text'] += '\n'
        for s in processedSentences:
            s['words'] = self.tp.tokenizer.tokenize(s['text'])
            for word in s['words']:
                word['wf'] = self.tp.cleaner.clean_social_networks(word['wf'])
        return processedSentences

    def get_sentences(self, posts, defaultMeta=None):
        """
        Iterate over sentences in the posts (a dictionary) and comments.
        """
        if defaultMeta is None:
            defaultMeta = {}
        for post in posts.values():
            curSentences = []
            if 'date' in post:
                year = int(post['date'][:4])
            else:
                year = None
            if 'author' not in post:
                post['author'] = ''
            if 'repost_sentences' in post:
                curSentences += self.get_post_sentences(post['repost_sentences'],
                                                        post['author'], defaultMeta, 'repost',
                                                        year=year)
            if 'sentences' in post:
                curSentences += self.get_post_sentences(post['sentences'],
                                                        post['author'], defaultMeta, 'post',
                                                        year=year)
            for cID in sorted(post['comments']):
                comment = post['comments'][cID]
                if 'sentences' in comment:
                    year = int(comment['date'][:4])
                    curSentences += self.get_post_sentences(comment['sentences'],
                                                            comment['author'], defaultMeta, 'comment',
                                                            year=year)
            if len(curSentences) > 0:
                curSentences[-1]['last'] = True
            for s in curSentences:
                yield s

    def convert_file(self, fnameSrc, fnameTarget):
        if fnameSrc == fnameTarget:
            return 0, 0, 0

        fIn = open(fnameSrc, 'r', encoding='utf-8-sig')
        data = json.loads(fIn.read())
        fIn.close()
        if 'meta' not in data or 'posts' not in data:
            return 0, 0, 0

        authorMeta = {k: data['meta'][k] for k in data['meta']
                      if k in self.allowedMetaKeys}
        textJSON = {'meta': data['meta'], 'sentences': []}
        if 'title' not in textJSON['meta'] and 'screen_name' in textJSON['meta']:
            textJSON['meta']['title'] = data['meta']['screen_name']
        nTokens, nWords, nAnalyzed = 0, 0, 0
        textJSON['sentences'] = [s for s in self.get_sentences(data['posts'], authorMeta)]
        self.tp.splitter.recalculate_offsets(textJSON['sentences'])
        self.tp.splitter.add_next_word_id(textJSON['sentences'])
        for s in textJSON['sentences']:
            curTokens, curWords, curAnalyzed =\
                self.tp.parser.analyze_sentence(s, self.corpusSettings['languages'][s['lang']])
            nTokens += curTokens
            nWords += curWords
            nAnalyzed += curAnalyzed
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyzed


if __name__ == '__main__':
    t2j = SocialNetworks2JSON()
    t2j.process_corpus()
