import os
import re
import json
import gzip
import time
from lxml import etree
from simple_convertors.text_processor import TextProcessor
from json2cg import JSON2CG


class Txt2JSON:
    """
    Contains methods to make JSONs ready for indexing from
    raw text files, a csv with metadata and a list with parsed
    word forms.
    """

    rxStripDir = re.compile('^.*[/\\\\]')
    rxStripExt = re.compile('\\.[^.]*$')
    rxGoodTag = re.compile('^\\w[\\w_-]*$')
    rxEmptyValueComa = re.compile('^[ \t.?()]*$')

    def __init__(self, settingsDir='conf_conversion'):
        """
        Load settings, including corpus name and directory, from the
        conversion_settings.json file in settings directory. Then load all other
        settings from the corpus directory. These may override the
        initially loaded settings.

        Simplified scenario:
        - only one corpus at any given time in src_convertors/corpus
        - no src_convertors/conf_conversion folder or empty corpus name in
        src_convertors/conf_conversion/conversion_settings.json
        In this case, treat src_convertors/corpus as the corpus directory
        and load settings from src_convertors/corpus/conf_conversion.
        """
        if not os.path.exists(settingsDir) and os.path.exists('conf'):
            # Backward compatibility: check the old name of configuration folder
            settingsDir = 'conf'
        self.errorLog = ''
        self.settingsDir = settingsDir
        self.corpusSettings = {'corpus_dir': 'corpus'}
        if os.path.exists(self.settingsDir):
            self.load_settings(corpusSpecific=False)
            if len(self.corpusSettings['corpus_name']) > 0:
                self.corpusSettings['corpus_dir'] = os.path.join(self.corpusSettings['corpus_dir'],
                                                                 self.corpusSettings['corpus_name'])

        self.settingsDir = os.path.join(self.corpusSettings['corpus_dir'],
                                        settingsDir)
        if (not os.path.exists(self.settingsDir)
                and os.path.exists(os.path.join(self.corpusSettings['corpus_dir'], 'conf'))):
            # Backward compatibility: check the old name of configuration folder
            self.settingsDir = os.path.join(self.corpusSettings['corpus_dir'],
                                            'conf')
        self.load_settings(corpusSpecific=True)

        fCategories = open(os.path.join(self.settingsDir, 'categories.json'), 'r',
                           encoding='utf-8-sig')
        self.categories = json.loads(fCategories.read())
        fCategories.close()
        self.meta = {}
        self.speakerMeta = {}
        self.tp = TextProcessor(settings=self.corpusSettings,
                                categories=self.categories,
                                errorLog=self.errorLog)
        self.excludeByMetaRules = []
        if 'exclude_by_meta' in self.corpusSettings:
            self.excludeByMetaRules = self.corpusSettings['exclude_by_meta']
        self.srcExt = 'txt'

    def load_settings(self, corpusSpecific=False):
        """
        Load settings from the general settings file or
        the corpus-specific settings file (the latter may
        override the general settings loaded earlier).
        Clean the error log file, if any.
        """
        try:
            fCorpus = open(os.path.join(self.settingsDir, 'conversion_settings.json'), 'r',
                           encoding='utf-8-sig')
        except IOError:
            # Obsolete settings file name; I keep it here for backward compatibility
            fCorpus = open(os.path.join(self.settingsDir, 'corpus.json'), 'r',
                           encoding='utf-8-sig')
        localSettings = json.loads(fCorpus.read())
        if corpusSpecific:
            if 'corpus_dir' in localSettings:
                del localSettings['corpus_dir']     # This key should not be overwritten
        self.corpusSettings.update(localSettings)
        if self.corpusSettings['json_indent'] < 0:
            self.corpusSettings['json_indent'] = None
        fCorpus.close()
        if 'error_log' in self.corpusSettings:
            self.errorLog = self.corpusSettings['error_log']
            try:
                # Clean the log
                fLog = open(self.errorLog, 'w', encoding='utf-8')
                fLog.close()
            except:
                pass

    def log_message(self, message):
        """
        If the filename of the error log is not empty, append
        the message to the file.
        """
        if self.errorLog is None or len(self.errorLog) <= 0:
            return
        try:
            fLog = open(self.errorLog, 'a', encoding='utf-8')
            fLog.write(message + '\n')
            fLog.close()
        except:
            return

    def load_meta_csv(self, fnameMeta):
        """
        Load the metadata for the files of the corpus from a tab-delimited
        metadata file whose name is indicated in the settings.
        """
        fMeta = open(fnameMeta, 'r', encoding='utf-8-sig')
        for line in fMeta:
            if len(line) <= 3:
                continue
            metaValues = line.split('\t')
            curMetaDict = {}
            for i in range(len(self.corpusSettings['meta_fields'])):
                fieldName = self.corpusSettings['meta_fields'][i]
                if i >= len(metaValues):
                    break
                if fieldName == 'filename':
                    metaValues[i] = metaValues[i].replace('\\', '/')
                    if not self.corpusSettings['meta_files_case_sensitive']:
                        metaValues[i] = metaValues[i].lower()
                    self.meta[metaValues[i]] = curMetaDict
                else:
                    curMetaDict[fieldName] = metaValues[i].strip()
        fMeta.close()

    def add_coma_key_to_meta(self, dictMeta, el, fname):
        """
        Add metadata for a single key-value pair represented
        as an XML element taken from the COMA file.
        """
        if 'Name' not in el.attrib or 'coma_meta_conversion' not in self.corpusSettings:
            return
        if re.search('\\b[Dd]ate +of +recording\\b', el.attrib['Name']) is not None:
            # Ad-hoc for the date of creation
            # Ignore dates in round brackets
            truncatedText = el.text
            if "(" in el.text:
                truncatedText = el.text[0:el.text.find("(")]
            # For approximate recoring dates (e.g., '1979 to 1983', '1979-1983'), use both
            # Dates such as '1880s to 1890s' are also handled
            m = re.findall(r'(?:^|\s|-)([0-9]{4}s{0,1})', truncatedText)
            if len(m) > 0:
                dictMeta['year_from'] = m[0][:-1] if m[0].endswith("s") else m[0]
                if len(m) == 1:
                    dictMeta['year_to'] = m[0][:-1] if m[0].endswith("s") else m[0]
                else:
                    if int(m[1].rstrip('s')) >= int(m[0].rstrip('s')):
                        dictMeta['year_to'] = f'{m[1][:-2]}9' if m[1].endswith("s") else m[1]
                    else:
                        # Inverted order of dates ('2000s or 1990s')
                        dictMeta['year_from'] = m[1][:-1] if m[1].endswith("s") else m[1]
                        dictMeta['year_to'] = f'{m[0][:-2]}9' if m[0].endswith("s") else m[0]
            else:
                # e.g., 197X
                m = re.search('^([12][0-9])([0-9X])X\\b', truncatedText)
                if m is not None:
                    if m.group(2) in ('X', 'x', 'Х', 'х'):
                        dictMeta['year_from'] = int(m.group(1)) * 100
                        dictMeta['year_to'] = dictMeta['year_from'] + 99
                    else:
                        dictMeta['year_from'] = int(m.group(1)) * 100 + int(m.group(2)) * 10
                        dictMeta['year_to'] = dictMeta['year_from'] + 9
                    dictMeta['year_from'] = str(dictMeta['year_from'])
                    dictMeta['year_to'] = str(dictMeta['year_to'])

        elif el.attrib['Name'] in self.corpusSettings['coma_meta_conversion']:
            dictMeta[self.corpusSettings['coma_meta_conversion'][el.attrib['Name']]] = el.text.strip()

    def extract_value_coma(self, node, xpathValue):
        els = node.xpath(xpathValue)
        result = []
        for el in els:
            if (el.text is not None
                    and self.rxEmptyValueComa.search(el.text) is None):
                result.append(el.text.strip())
        if len(result) <= 0:
            return ''
        elif len(result) == 1:
            return result[0]
        return result

    def load_speaker_meta_coma(self, srcTree):
        """
        Load speakers' data from Coma.
        """
        speakerMeta = {}     # code -> speaker metadata as a dictionary
        speakerNodes = srcTree.xpath('//Corpus/CorpusData/Speaker')
        for s in speakerNodes:
            sJson = {}
            if 'Id' not in s.attrib:
                continue
            # sJson['id'] = s.attrib['Id']
            code = self.extract_value_coma(s, 'Sigle')
            speakerMeta[code] = sJson
            metaMapping = {}
            if 'coma_meta_speaker_conversion' in self.corpusSettings:
                metaMapping = self.corpusSettings['coma_meta_speaker_conversion']
            for metaKeyComa, metaKeyTsakorpus in metaMapping.items():
                if self.rxGoodTag.search(metaKeyComa) is not None:
                    metaKeyComa = metaKeyComa + '|Location/Description/Key[@Name=\'' + metaKeyComa + "']"
                else:
                    metaKeyComa = 'Location/Description/Key[@Name=\'' + metaKeyComa + "']"
                value = self.extract_value_coma(s, metaKeyComa)
                if len(value) > 0:
                    sJson[metaKeyTsakorpus] = value
            if 'coma_meta_speaker_lang_conversion' in self.corpusSettings:
                for l in s.xpath('Language[@Type=\'L1\']'):
                    for metaKeyComa, metaKeyTsakorpus in self.corpusSettings['coma_meta_speaker_lang_conversion'].items():
                        metaKeyComa = 'Description/Key[@Name=\'' + metaKeyComa + "']"
                        value = self.extract_value_coma(l, metaKeyComa)
                        if len(value) > 0:
                            if metaKeyTsakorpus in sJson:
                                if type(sJson[metaKeyTsakorpus]) == str:
                                    sJson[metaKeyTsakorpus] = [sJson[metaKeyTsakorpus]]
                                if type(value) == str:
                                    value = [value]
                                sJson[metaKeyTsakorpus] += value
                            sJson[metaKeyTsakorpus] = value
        return speakerMeta

    def load_meta_coma(self, fnameMeta):
        """
        Load the communication-level metadata for the files of the corpus
        from a Coma XML file whose name is indicated in the settings.
        """
        srcTree = etree.parse(fnameMeta)
        self.speakerMeta = self.load_speaker_meta_coma(srcTree)
        communications = srcTree.xpath('//Corpus/CorpusData/Communication')
        for c in communications:
            if 'Name' not in c.attrib:
                continue
            title = c.attrib['Name'].strip()
            fname = ''
            curMetaDict = {}
            exbTranscrs = c.xpath('Transcription')
            exbDescrs = c.xpath('Description|'
                                'Setting/Description|'
                                'Location/Description')
            for exbTranscr in exbTranscrs:
                elFname = exbTranscr.xpath('Filename')
                if (len(elFname) > 0 and elFname[0].text is not None
                        and elFname[0].text.lower().endswith(('.exb', '.eaf'))):
                    fname = elFname[0].text
                    if not self.corpusSettings['meta_files_ext']:
                        fname = re.sub('\\.[^.]*$', '', fname)
                elTitle = exbTranscr.xpath('Filename')
                if len(title) <= 0 and len(elTitle) > 0 and elTitle[0].text is not None:
                    title = elTitle[0].text
            for exbDescr in exbDescrs:
                for descrKey in exbDescr:
                    if descrKey.tag != 'Key':
                        continue
                    self.add_coma_key_to_meta(curMetaDict, descrKey, fname)
            if len(fname) > 0:
                if 'title' not in curMetaDict:
                    if len(title) > 0:
                        curMetaDict['title'] = title
                    else:
                        curMetaDict['title'] = fname
                self.meta[fname] = curMetaDict
                if title != fname and title not in self.meta:
                    self.meta[title] = curMetaDict

    def load_meta(self):
        """
        Look at the metadata file extension, if any, and call the
        appropriate function for loading the metadata.
        """
        self.meta = {}
        if len(self.corpusSettings['meta_filename']) <= 0:
            return
        fnameMeta = os.path.join(self.corpusSettings['corpus_dir'],
                                 self.corpusSettings['meta_filename'])
        if not os.path.exists(fnameMeta):
            print('Metadata file not found.')
            return
        if self.corpusSettings['meta_filename'].lower().endswith('.coma'):
            self.load_meta_coma(fnameMeta)
        else:
            self.load_meta_csv(fnameMeta)

    def write_output(self, fnameTarget, textJSON):
        """
        Write the JSON text to fnameTarget either as plain text
        or as gzipped text, depending on the settings.
        """
        if self.corpusSettings['gzip']:
            fTarget = gzip.open(fnameTarget, 'wt', encoding='utf-8')
        else:
            fTarget = open(fnameTarget, 'w', encoding='utf-8')
        json.dump(textJSON, fp=fTarget, ensure_ascii=False, sort_keys=True,
                  indent=self.corpusSettings['json_indent'])
        fTarget.close()

    def get_meta(self, fname):
        """
        Return dictionary with metadata for the given filename.
        The metadata are taken from the dictionary self.meta,
        which has to be loaded before the conversion starts.
        If the metadata are not found, return a dictionary with
        only the filename field.
        """
        fname2check = fname
        curMeta = {'filename': fname}
        if not self.corpusSettings['meta_files_dir']:
            fname2check = self.rxStripDir.sub('', fname2check)
        elif fname2check.startswith(os.path.join(self.corpusSettings['corpus_dir'], self.srcExt)):
            fname2check = fname2check[len(os.path.join(self.corpusSettings['corpus_dir'], self.srcExt)) + 1:].replace('\\', '/')
        if not self.corpusSettings['meta_files_ext']:
            fname2check = self.rxStripExt.sub('', fname2check)
        if not self.corpusSettings['meta_files_case_sensitive']:
            fname2check = fname2check.lower()
        if fname2check not in self.meta:
            print('File not in meta:', fname)
            if 'nometa_skip' in self.corpusSettings and self.corpusSettings['nometa_skip']:
                return None
        else:
            curMeta.update(self.meta[fname2check])
        return curMeta

    def exclude_text(self, meta):
        """
        Check if the file should be excluded from output based on the
        metadata rules specified in "exclude_by_meta" in conversion_settings.json.
        """
        for rule in self.excludeByMetaRules:
            if all(k in meta and meta[k] == rule[k] for k in rule):
                self.log_message('File excluded by meta: ' + json.dumps(meta, ensure_ascii=False)
                                 + ' (rule: ' + json.dumps(rule, ensure_ascii=False) + ').')
                return True
        return False

    def convert_file(self, fnameSrc, fnameTarget):
        """
        Take one text file fnameSrc, turn it into a parsed JSON file
        ready for indexing and write the output to fnameTarget.
        Return number of tokens, number of words and number of
        words with at least one analysis in the document.
        """
        if fnameSrc == fnameTarget:
            return 0, 0, 0

        curMeta = self.get_meta(fnameSrc)
        if self.exclude_text(curMeta):
            return 0, 0, 0
        textJSON = {'meta': curMeta, 'sentences': []}
        fSrc = open(fnameSrc, 'r', encoding='utf-8')
        text = fSrc.read()
        fSrc.close()

        textJSON['sentences'], nTokens, nWords, nAnalyze = self.tp.process_string(text)
        self.write_output(fnameTarget, textJSON)
        return nTokens, nWords, nAnalyze

    def process_corpus(self):
        """
        Take every text file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        This is the main function of the class.
        """
        if self.corpusSettings is None or len(self.corpusSettings) <= 0:
            return
        tStart = time.time()
        self.load_meta()
        nTokens, nWords, nAnalyzed = 0, 0, 0
        if self.srcExt != 'json':
            srcDir = os.path.join(self.corpusSettings['corpus_dir'], self.srcExt)
        else:
            srcDir = os.path.join(self.corpusSettings['corpus_dir'], 'json_input')
        targetDir = os.path.join(self.corpusSettings['corpus_dir'], 'json')
        for path, dirs, files in os.walk(srcDir):
            for filename in files:
                if not filename.lower().endswith('.' + self.srcExt):
                    continue
                targetPath = path.replace(srcDir, targetDir)
                if targetPath == path:
                    continue    # this should never happen, but just in case
                if not os.path.exists(targetPath):
                    os.makedirs(targetPath)
                fnameSrc = os.path.join(path, filename)
                fnameTarget = os.path.join(targetPath, filename)
                fextTarget = '.json'
                if self.corpusSettings['gzip']:
                    fextTarget = '.json.gz'
                fnameTarget = self.rxStripExt.sub(fextTarget, fnameTarget)
                self.log_message('Processing ' + fnameSrc + '...')
                curTokens, curWords, curAnalyzed = self.convert_file(fnameSrc, fnameTarget)
                nTokens += curTokens
                nWords += curWords
                nAnalyzed += curAnalyzed
        tEnd = time.time()
        print('Conversion to JSON finished in', tEnd - tStart, 's.', nTokens, 'tokens total,', nWords, 'words total.')
        if nWords > 0:
            print(nAnalyzed, 'words parsed (' + str(nAnalyzed / nWords * 100) + '%).')
        if 'cg_disambiguate' in self.corpusSettings and self.corpusSettings['cg_disambiguate']:
            translator = JSON2CG(self.settingsDir,
                                 self.corpusSettings['corpus_dir'],
                                 self.corpusSettings['corpus_name'])
            translator.process_corpus()


if __name__ == '__main__':
    t2j = Txt2JSON()
    t2j.process_corpus()
