# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import random
import string
import re
from typing import List, Optional

from pyrit.models import PromptDataType
from pyrit.prompt_converter import PromptConverter, ConverterResult


class InsertPunctuationConverter(PromptConverter):
    """
    Inserts punctuation into a prompt to test robustness.
    Punctuation insertion: inserting single punctuations in string.punctuation.
    Words in a prompt: a word does not contain any punctuation and space.
    "a1b2c3" is a word; "a1 2" are 2 words; "a1,b,3" are 3 words.
    """

    default_punctuation_list = [",", ".", "!", "?", ":", ";", "-"]

    def __init__(self, max_iterations: int = 10, word_swap_ratio: float = 0.2, between_words: bool = True) -> None:
        """
        Initialize the converter with optional max iterations and word swap ratio.
        Args:
            max_iterations (int): Number of prompts to generate. Defaults to 10.
            word_swap_ratio (float): Percentage of words to perturb. Defaults to 0.2.
            between_words (bool): If True, insert punctuation only between words.
                                  If False, insert punctuation within words. Defaults to True.
        """
        # swap ratio cannot be 0 or larger than 1
        if not 0 < word_swap_ratio <= 1:
            raise ValueError("word_swap_ratio must be between 0 to 1, as (0, 1].")

        # max iterations should be at least 1
        if max_iterations < 1:
            raise ValueError("max_iterations must be greater than 0.")

        self._max_iterations = max_iterations
        self._word_swap_ratio = word_swap_ratio
        self._between_words = between_words

    def _is_valid_punctuation(self, punctuation_list: List[str]) -> bool:
        """
        Check if all items in the list are valid punctuation characters in string.punctuation.
        Space, letters, numbers, double punctuations are all invalid.
        Args:
            punctuation_list (List[str]): List of punctuations to validate.
        Returns:
            bool: valid list and valid punctuations
        """
        return all(str in string.punctuation for str in punctuation_list)

    async def convert_async(
        self, *, prompt: str, input_type: PromptDataType = "text", punctuation_list: Optional[List[str]] = None
    ) -> ConverterResult:
        """
        Convert the given prompt by inserting punctuation.
        Args:
            prompt (str): The text to convert.
            input_type (PromptDataType): The type of input data.
            punctuation_list (Optional[List[str]]): List of punctuations to use for insertion.
        Returns:
            ConverterResult: A ConverterResult containing the interations of modified prompts.
        """
        if not self.input_supported(input_type):
            raise ValueError("Input type not supported")

        # initialize default punctuation list
        # if not specified, defaults to defaul_punctuation_list
        if punctuation_list is None:
            punctuation_list = self.default_punctuation_list
        # if empty, raise ValueError
        elif not punctuation_list:
            raise ValueError("punctuation_list cannot be empty")
        # check if provided punctuations are valid
        elif not self._is_valid_punctuation(punctuation_list):
            raise ValueError(
                f"Invalid punctuations: {punctuation_list}."
                f" Only single characters from {string.punctuation} are allowed."
            )

        # generate number of max_iterations modified prompts with punctuation insertions.
        modified_prompts = [self._insert_punctuation(prompt, punctuation_list) for _ in range(self._max_iterations)]
        # combine all modified prompts into a single result
        final_prompt = "\n".join(modified_prompts)

        return ConverterResult(output_text=final_prompt, output_type="text")

    def _insert_punctuation(self, prompt: str, punctuation_list: List[str]) -> str:
        """
        Insert punctuation into the prompt.
        Args:
            prompt (str): The text to modify.
            punctuation_list (List[str]): List of punctuations for insertion.
        Returns:
            str: The modified prompt with inserted punctuation from helper method.
        """
        # words list contains single spaces, single word without punctuations, single punctuations
        words = re.findall(r"\w+|[^\w\s]|\s", prompt)
        # maintains indices for actual "words", i.e. letters and numbers not divided by punctuations
        word_indices = [i for i in range(0, len(words)) if not re.match(r"\W", words[i])]
        # calculate the number of insertions
        num_insertions = max(
            1, round(len(word_indices) * self._word_swap_ratio)
        )  # Ensure at least one punctuation is inserted

        # if there's no actual word without punctuations in the list, insert random punctuation at position 0
        if not word_indices:
            return random.choice(punctuation_list) + prompt
        # insert between words if _between_words = True
        if self._between_words:
            return self._insert_between_words(words, word_indices, num_insertions, punctuation_list)
        else:
            return self._insert_within_words(prompt, num_insertions, punctuation_list)

    def _insert_between_words(
        self, words: List[str], word_indices: List[int], num_insertions: int, punctuation_list: List[str]
    ) -> str:
        """
        Insert punctuation between words in the prompt.
        Args:
            words (List[str]): List of words and punctuations.
            word_indices (List[int]): Indices of the actual words without punctuations in words list.
            num_insertions (int): Number of punctuations to insert.
            punctuation_list (List[str]): punctuations for insertion.

        Returns:
            str: The modified prompt with inserted punctuation.
        """
        insert_indices = random.sample(word_indices, num_insertions)
        INSERT_BEFORE = 0
        INSERT_AFTER = 1
        # randomly choose num_insertions indices from actual word indices.
        for index in insert_indices:
            # either insert random punctuation before or at the end of random actual word in words list.
            if random.randint(INSERT_BEFORE, INSERT_AFTER) == INSERT_AFTER:
                words[index] += random.choice(punctuation_list)
            else:
                words[index] = random.choice(punctuation_list) + words[index]
        # join the words list and return a modified prompt
        return "".join(words).strip()

    def _insert_within_words(self, prompt: str, num_insertions: int, punctuation_list: List[str]) -> str:
        """
        Insert punctuation at any indices in the prompt, can insert into a word.
        Args:
            promp str: The prompt string
            num_insertions (int): Number of punctuations to insert.
            punctuation_list (List[str]): punctuations for insertion.
        Returns:
            str: The modified prompt with inserted punctuation.
        """
        # list of chars in the prompt string
        prompt_list = list(prompt)
        # store random indices of prompt_list into insert_indices
        # if the prompt has only 0 or 1 chars, insert at the end of the prompt
        insert_indices = (
            [1] if len(prompt_list) <= num_insertions else random.sample(range(0, len(prompt_list) - 1), num_insertions)
        )

        for index in insert_indices:
            # insert into prompt_list at the insert_indices with random punctuation from the punctuaion_list
            prompt_list.insert(index, random.choice(punctuation_list))

        return "".join(prompt_list).strip()

    def input_supported(self, input_type: PromptDataType) -> bool:
        return input_type == "text"