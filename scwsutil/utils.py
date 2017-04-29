#-*-coding=utf-8-*-

import re
import os
import scws


SCWS_ENCODING = 'utf-8'
SCWS_RULES = '/usr/local/scws/etc/rules.utf8.ini'
CHS_DICT_PATH = '/usr/local/scws/etc/dict.utf8.xdb'
CHT_DICT_PATH = '/usr/local/scws/etc/dict_cht.utf8.xdb'
IGNORE_PUNCTUATION = 1

ABSOLUTE_DICT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../dict'))
CUSTOM_DICT_PATH = os.path.join(ABSOLUTE_DICT_PATH, 'userdic.txt')
EXTRA_STOPWORD_PATH = os.path.join(ABSOLUTE_DICT_PATH, 'stopword.txt')
EXTRA_EMOTIONWORD_PATH = os.path.join(ABSOLUTE_DICT_PATH, 'emotionlist.txt')
EXTRA_ONE_WORD_WHITE_LIST_PATH = os.path.join(ABSOLUTE_DICT_PATH, 'one_word_white_list.txt')


def load_scws():
    s = scws.Scws()
    s.set_charset(SCWS_ENCODING)

    s.set_dict(CHS_DICT_PATH, scws.XDICT_MEM)
    s.add_dict(CHT_DICT_PATH, scws.XDICT_MEM)
    s.add_dict(CUSTOM_DICT_PATH, scws.XDICT_TXT)

    # 把停用词全部拆成单字，再过滤掉单字，以达到去除停用词的目的
    s.add_dict(EXTRA_STOPWORD_PATH, scws.XDICT_TXT)
    # 即基于表情表对表情进行分词，必要的时候在返回结果处或后剔除
    s.add_dict(EXTRA_EMOTIONWORD_PATH, scws.XDICT_TXT)

    s.set_rules(SCWS_RULES)
    s.set_ignore(IGNORE_PUNCTUATION)
    return s


def load_emotion_words():
    emotion_words = [line.strip('\r\n') for line in file(EXTRA_EMOTIONWORD_PATH)]
    return emotion_words


def load_one_words():
    one_words = [line.strip('\r\n') for line in file(EXTRA_ONE_WORD_WHITE_LIST_PATH)]
    return one_words


single_word_whitelist = set(load_one_words())
single_word_whitelist |= set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789')


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print '%r %2.2f sec' % (method.__name__, te - ts)
        return result
    return timed


class SimpleMapReduce(object):
    def __init__(self, map_func, reduce_func, num_workers=None):
        self.map_func = map_func
        self.reduce_func = reduce_func
        self.num_workers = multiprocessing.cpu_count() * 2

    def partition(self, mapped_values):
        """
        >>> s = [('yellow', 1), ('blue', 2), ('yellow', 3), ('blue', 4), ('red', 1)]
        >>> d = collections.defaultdict(list)
        >>> for k, v in s:
        ...     d[k].append(v)
        ...
        >>> d.items()
        [('blue', [2, 4]), ('red', [1]), ('yellow', [1, 3])]
        """

        partitioned_data = collections.defaultdict(list)
        for key, value in mapped_values:
            partitioned_data[key].append(value)
        return partitioned_data.items()

    def __call__(self, inputs, chunksize=1):
        if inputs == []:
            return []
        self.pool = multiprocessing.Pool(self.num_workers, maxtasksperchild=10000)
        map_responses = self.pool.map(self.map_func, inputs, chunksize=chunksize)
        partitioned_data = self.partition(itertools.chain(*map_responses))
        reduced_values = self.pool.map(self.reduce_func, partitioned_data)
        # recycle processes
        self.pool.close()
        self.pool.join()

        return reduced_values


def top_keywords(get_results, top=1000):
    keywords_with_count = keywords(get_results)
    keywords_with_count.sort(key=operator.itemgetter(1))

    return keywords_with_count[len(keywords_with_count) - top:]


def not_low_freq_keywords(get_results, larger_than=3):
    keywords_with_count = keywords(get_results)
    keywords_with_count = [x for x in keywords_with_count if x[1] > larger_than]
    return keywords_with_count


@timeit
def keywords(get_results):
    origin_data = []
    for r in get_results():
        origin_data.append(r['terms'].items())

    mapper = SimpleMapReduce(addcount2keywords, count_words)
    keywords_with_count = mapper(origin_data)

    return keywords_with_count


def addcount2keywords(origin_keywords_with_count):
    keywords_with_count = []
    for k, v in origin_keywords_with_count:
        keywords_with_count.append((k, v))
    return keywords_with_count


def count_words(item):
    word, occurances = item
    return (word, sum(occurances))


def cut(s, text, f=None, cx=False):
    if f:
        tks = [token for token
               in s.participle(cut_filter(text))
               if token[1] in f and (3 < len(token[0]) < 30 or token[0] in single_word_whitelist)]
    else:
        tks = [token for token
               in s.participle(cut_filter(text))
               if 3 < len(token[0]) < 30 or token[0] in single_word_whitelist]

    if cx:
        return tks
    else:
        return [tk[0] for tk in tks]


def cut_filter(text):
    pattern_list = [r'\（分享自 .*\）', r'http://t.cn/\w*']
    for i in pattern_list:
        p = re.compile(i)
        text = p.sub('', text)
    return text

cx_dict_noun = set(['Ng','n','nr','ns','nt','nz']) # 关键词词性词典, 保留名词

EXTRA_BLACK_LIST_PATH = os.path.join(ABSOLUTE_DICT_PATH, "black.txt")

def load_black_words():
    one_words = set([line.strip('\r\n') for line in file(EXTRA_BLACK_LIST_PATH)])
    return one_words

black_words = load_black_words()

def cut_words_noun(s, text):
    '''分词, 加入黑名单过滤单个词，保留名词
       input
           texts: 输入text，utf-8
       output:
           terms: 关键词list
    '''
    if not isinstance(text, str):
        raise ValueError("cut words input text must be string")

    cx_terms = cut(s, text, cx=True)

    return [term for term, cx in cx_terms if cx in cx_dict_noun and term not in black_words]
