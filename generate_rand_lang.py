
'''
a script for generating a random language with changable characteristics

---

Теперь всё так:
1. Исходя из кол-ва токенов в корпусе, вычисляем кол-во словоформ, генерируем словоформы
без текстового выражения, но с частотностями
2. Исходя из формулы 1+a*f^b, частотности словоформ и средней длины слова частотности 1 
генерируем словам длину (и, видимо, на этом этапе можно и текстовое выражение)
3. Исходя из кол-ва POS и их фич, вычисляем кол-во лексем, приписываем каждой лексеме
нужное количество словоформ.

В конце этого этапа у нас есть список объектов класса Лексема со свойствами:
- POS
- лемма (т.е. одна из словоформ)
- парадигма (это, видимо, в виде словаря)

4. Исходя из среднего кол-ва омомнимичных разборов на одну словоформу и экспоненциального
распределения, нагенерить ещё лексем, так, чтобы получилось нужное кол-во разборов
5. Поприсваивать разборы словоформам (с учётом их частотностей, конечно)

На этом этапе у нас уже есть список объектов класса Словоформа со свойствами:
- частотность
- текстовое представление
- лексема
- список разборов

6. Имея все эти словоформы, генерируем с их помощью предложения и записаваем их 
в эти самые джейсонины

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


class WordForm():
	"""docstring for WordForm"""
	def __init__(self, freq):
		self.freq = freq


class Lexeme():
	"""docstring for Lexeme"""
	def __init__(self, pos):
		self.pos = pos
		

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
	
