#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author：Mervin 
# time:10/8/2019

import sys
from collections import defaultdict
import math
from openpyxl.compat import file

"""
Count n-gram frequencies in a data file and write counts to stdout
"""


def simple_conll_corpus_itertor(file):
    """
    Get an iterator object over the corpus file.
    The elements of the iterator contain(word, ne_tag) tuples. Blank lines,
    indicating sentence boundaries.
    :param file:
    :return: (None, None)
    """
    lines = file.readline()
    while 1:
        line = lines.strip()
        if line:
            """
            Nonempty line
            Extract information from line
            Each line has the format: Word pos_tag phrase_tag ne_tag
            """
            fields = line.split(" ")
            ne_tag = fields[-1]
            """
            phrase_tag = fields[-2]
            pos_tag = fields[-3]
            """
            word = " ".join(fields[:-1])
            yield word, ne_tag
        else:
            yield(None, None)
        lines = file.readline()


def sentence_iterator(corpus_iterator):
    """
    Return an iterator object that yield one sentence at a time
    Sentences are represented as lists of (word, ne_tag) tuples
    :param corpus_iterator:
    :return:
    """
    cur_sentence = []
    for l in corpus_iterator:
        if l == (None, None):
            if cur_sentence:  # Reach the end of the sentence
                yield cur_sentence
                cur_sentence = []
            else:
                sys.stderr.write("WARNING: Got empty input file/stream.\n")
                raise StopIteration
        else:
            cur_sentence.append(l)
    if cur_sentence:
        yield cur_sentence   # Otherwise when there is no more token in the stream return the last sentence.


def get_ngrams(sent_iterator, n):
    """
    Get a generator that returns n-grams over the entire corpus,
    respecting sentence boundaries and inserting boundary tokens.
    Sent_iterator is a generator object whose elements are lists of tokens.
    :param sent_iterator:
    :param n:
    :return:
    """
    for sent in sent_iterator:      # Add boundary symbols to the sentence
        w_boundary = (n-1)*[(None, '*')]
        w_boundary.extend(sent)
        w_boundary.append((None, "STOP"))
        ngrams = (tuple(w_boundary[i: i+n]) for i in range(len(w_boundary)-n+1))
        for n_gram in ngrams:
            yield n_gram


class Hmm(object):
    """
    Stores counts for n-grams and emissions
    """
    def __init__(self, n=3):
        assert n >= 2, "We except n>=2"
        self.n = n
        self.emission_counts = defaultdict(int)  # Create a like-dictionary object and values are instants of int
        self.ngram_counts = [defaultdict(int) for i in range(self.n)]
        self.all_states = set()

    def train(self, file):
        """
        Count N-gram frequencies and emission probabilities from a corpus file.
        :param file:
        :return:
        """
        ngram_iterator = get_ngrams(sentence_iterator(simple_conll_corpus_itertor(file)), self.n)
        for ngram in ngram_iterator:
            # Sanity check: n-gram we get from the corpus stream needs to have the right length
            assert len(ngram) == self.n, "ngram in stream is %i, expected %i" % (len(ngram, self.n))
            tagsonly = tuple([ne_tag for word, ne_tag in ngram])
            for i in range(2, self.n+ 1):   # count 2...n gram
                self.ngram_counts[i-1][tagsonly[-i:]] += 1
            if ngram[-1][0] is not None:
                self.ngram_counts[0][tagsonly[-1:]] += 1
                self.emission_counts[ngram[-1]] += 1
            if ngram[-2][0] is None:
                self.ngram_counts[self.n - 2][tuple((self.n - 1) * ["*"])] += 1

    def write_counts(self, output, printngrams=[1,2,3]):
        """
        Writes counts to the output file
        :param output:
        :param printngrams:
        :return:
        """
        for word, ne_tag in self.emission_counts:
            output.write("%i WORDTAG %s %s\n" % (self.emission_counts[(word, ne_tag)], ne_tag, word))
        for n in printngrams:
            for ngram in self.ngram_counts[n-1]:
                ngramstr = " ".join(ngram)
                output.write("%i %i-GRAM %s\n" % (self.ngram_counts[n-1][ngram], n, ngramstr))

    def read_count(self, corpusfile):
        self.n = 3
        self.emission_counts = defaultdict(int)
        self.ngram_counts = [defaultdict(int) for i in range(self.n)]
        self.all_states = set()

        for line in corpusfile:
            parts = line.strip().split(" ")
            count = float(parts[0])
            if parts[1] == "WORDTAG":
                ne_tag = parts[2]
                word = parts[3]
                self.emission_counts[(word, ne_tag)] = count
                self.all_states.add(ne_tag)
            elif parts[1].endswith("GRAM"):
                n = int(parts[1].replace("-GRAM", ""))
                ngram = tuple(parts[2:])
                self.ngram_counts[n - 1][ngram] = count

def usage():
    print("python count_freqs.py " +
          "[input_file]>[output_file]. Read in a gene tagged training input file and produce counts.")


if __name__ == "__main__":
    if len(sys.argv) != 2:     # Expect exactly one argument: the training data file
        usage()
        sys.exit(2)
    try:
        input = file(sys.argv[1], "r")
    except IOError:
        sys.stderr.write("ERROR: Cannot read inputfile %s.\n" % arg)
        sys.exit(1)

    # Initialize a trigram counter
    counter = Hmm(3)
    # Collect counts
    counter.train(input)
    # Write the counts
    counter.write_counts(sys.stdout)



