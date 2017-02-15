
'''
a script for generating a random language with changable characteristics

В общем, я это вижу так: 

- generate_words, исходя из кол-ва токенов, с помощью закона Ципфа, генерит словарь,
где ключи -- словоформы, а значения -- вероятность встретить эту лексему в тексте

- gram_analysys: я в процессе активного обдумывания, как и когда оно работает
пожалуй процитирую письмо: "При порождении списка слов нужно будет приписывать им "разборы". 
В настройках должны быть заданы среднее количество раззных разборов на одно слово и процент слов без разборов. 
При выборе значения категории нужно либо присваивать всем значениям равные вероятности (если список значений небольшой),
либо пользоваться тем же законом Ципфа, произвольно упорядочив значения (если список, скажем, хотя бы из 7 значений)."

- generate_sents, используя этот словарь, порождает предложения.

- generate_corp вызывает generate_sentsь, с помощью этого порождает тексты и записывает их в json.
при этом он измеряет кол-во токенов (видимо, держит их кол-во в какой-то переменной, и когда
оно достигает значения >= LENGTH_OF_CORPUS, прекращает порождать)

'''

import json
import string


ALPHABET = 'qwertyuiopasdfghjklzxcvbnmąóяŋ'
PUNKT = string.punctuation
MEAN_WORD_LENGTH = 5
MEAN_SENT_LENGTH = 10
MAX_SENT_LENGTH = 40
LENGTH_OF_CORPUS = 15*10^6 # in tokens, right?
with open('grammar_features.json') as f:
	GRAMMAR = json.load(f)


def generate_words():
	pass


def generate_sents(words_and_prob):
	pass


def gram_analysis():
	pass


def generate_corp():
	current_length = 0
	while current_length < LENGTH_OF_CORPUS:
		pass


if __name__ == '__main__':
	generate_corp()
	
