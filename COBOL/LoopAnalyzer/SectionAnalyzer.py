import os
import re
import sys
import copy
from FileManager import FileManager
import collections


class SectionAnalyzer:
    def __init__(self, text, cmd):
        self.text = text
        self.cmd = cmd

    @staticmethod
    def get_section(text, idx):
        """ Helper function to find a single section containing the idx line """
        start_idx = idx
        # Find the beginning of the section
        while idx > 0 and not SectionAnalyzer.is_section_line(text[start_idx]):
            start_idx -= 1
        if not SectionAnalyzer.is_section_line(text[start_idx]):
            raise RuntimeError("Can't find section for the line {}".format(text[start_idx]))

        # Find the end of the section
        end_idx = idx
        while end_idx + 1 < len(text) and not SectionAnalyzer.is_section_line(text[end_idx + 1]):
            end_idx += 1
        section_name = SectionAnalyzer.get_section_name(text[start_idx])
        return section_name, (start_idx, end_idx)

    @staticmethod
    def is_section_line(line):
        return True if re.search("\sSECTION\.", line) else False

    @staticmethod
    def get_section_name(line):
        elems = re.split("\s+", line)
        result = re.search("(\w|-)+", elems[1])
        assert result, f"not found section name: {line}"
        return result.group(0)

    def get_section_by_idxs(self, idxs):
        section_ranges = set()
        section_names = set()
        for idx in idxs:
            section_name, section_range = SectionAnalyzer.get_section(self.text, idx)
            section_names.add(section_name)
            section_ranges.add(section_range)
        return section_names, section_ranges

    def have_parent_section(self, section_name):
        perform_sec_str = f"\sPERFORM\s+{section_name}(\.)?\s"
        idxs = FileManager.get_str_idxs(self.text, perform_sec_str)
        if not idxs:
            return False
        else:
            return idxs

    def get_parent_section(self, idxs):
        """
        :return: set(), set()
        """
        # get all sections based on idxs
        cur_sec_names, cur_sec_ranges = self.get_section_by_idxs(idxs)
        return cur_sec_names, cur_sec_ranges

    def identify_all_rela_section(self):
        """
        Recursively find and extract the section containing a command and all its parent sections.
        """
        def find_all_parents(section_name, section_names, section_ranges, parents_dict):
            idxs = self.have_parent_section(section_name)
            # stop when no parents or section_name="MAIN", prevent from infinite recursion like Gr5reien KS24
            if not idxs or section_name == "MAIN":
                parents_dict[section_name] |= set()
                return
            cur_sec_names, cur_sec_ranges = self.get_parent_section(idxs)
            parents_dict[section_name] |= cur_sec_names
            section_names |= cur_sec_names
            section_ranges |= cur_sec_ranges
            for cur_sec_name in cur_sec_names:
                if cur_sec_name in parents_dict.keys():
                    continue
                find_all_parents(cur_sec_name, section_names, section_ranges, parents_dict)

        sections = []
        parents_dict = collections.defaultdict(set)
        # get the line No including cmd
        idxs = FileManager.get_str_idxs(self.text, self.cmd)
        # get all sections including line No.
        section_names, section_ranges = self.get_section_by_idxs(idxs)
        # get the parent section which using the current section
        for section_name in copy.deepcopy(section_names):
            find_all_parents(section_name, section_names, section_ranges, parents_dict)

        for start, end in sorted(section_ranges, key=lambda x: x[0]):
            sections.extend(self.text[start:end + 1])
        return sections, parents_dict,
