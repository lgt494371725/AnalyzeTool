import collections
import os
import re
import copy
import sys
from FileManager import FileManager
from SectionAnalyzer import SectionAnalyzer
import logging

logger = logging.getLogger(__name__)


class LoopAnalyzer:
    def __init__(self, text, cmd, parents_dict):
        self.text = text
        self.cmd = cmd
        self.parents_dict = parents_dict
        self.loop_dict = dict()

    def get_loop_dict(self):
        return self.loop_dict

    def calc_loop_counts(self):
        def find_max_sec_sum(sec, cur_sum):
            nonlocal max_v, sec_val_dict
            cur_sum += sec_val_dict[sec]
            if cur_sum > 30:
                logger.debug("infinite recursion found for section: %s", sec)
                max_v = 99999
                return
            if not self.parents_dict[sec]:
                max_v = max(max_v, cur_sum)
            else:
                for parent in self.parents_dict[sec]:
                    find_max_sec_sum(parent, cur_sum)

        logger.info("Starting to calculate loop counts.")
        try:
            sec_val_dict = {}
            for sec, str_value in self.loop_dict.items():
                sec_val_dict[sec] = self.get_loop_value(str_value)
            # calc every section's value including its parents
            max_v = -1
            for sec in sec_val_dict:
                find_max_sec_sum(sec, cur_sum=0)
            return max_v
            logger.info("Loop counts calculated successfully.")
        except Exception as e:
            logger.exception("Failed to calculate loop counts.")

    def get_loop_value(self, string):
        if not string:
            return 0
        if string == "PERFORMGOTO":
            return 2
        elif string in ("GOTO", "PERFORM"):
            return 1
        else:
            raise RuntimeError("incorrect input for loop definition")

    @staticmethod
    def is_label_line(line):
        elems = re.split("\s+", line)
        assert re.match("\d{6}", elems[0]), f"ERROR in is_label_line: {line}"
        if re.search("^(\w|-)+\.$", elems[1]):
            return True
        else:
            return False

    def is_GOTO_loop(self, idx):
        """
        identify is there a GOTO_loop around the given line No in current section
        1) identify if there is a label including 1)'s line. if there is, extract the label range
        here, label's start is " [LABELNAME].", label's end is the end of file or encounter another label.
        2) identify is there a GO TO [label] in the label range and the [label] should be the same as the name of currrent label range,
            which means there is a loop.
        label's definition:in the front of line except the row number, label name don't include space.
        """
        # Find the preceding label
        label_start = idx
        while label_start > 0 and not LoopAnalyzer.is_label_line(self.text[label_start]):
            label_start -= 1

        # label not found, like file KA60 in Gr5-denji
        if not LoopAnalyzer.is_label_line(self.text[label_start]):
            return False

        label_end = idx
        while label_end + 1 < len(self.text) and not LoopAnalyzer.is_label_line(self.text[label_end + 1]):
            label_end += 1

        # Append the label content if it's not already included
        assert label_end > label_start, "identify_GOTO_loop function Error"
        label = LoopAnalyzer.get_label_name(self.text[label_start])
        label_range = self.text[label_start:label_end + 1]
        if self.is_GOTO_line(label, label_range):
            # labels.extend(text[label_start:label_end + 1])
            return True
        return False

    def is_GOTO_line(self, label, text):
        for line in text:
            if re.search("\sGO\s+TO\s+", line):
                # print(line)
                go_to_label = re.search("\sGO\s+TO\s+((\w|-|\.)+)", line).group(1)
                # sometimes GO TO [label], [label] may not include "."
                if go_to_label.replace(".", "") == label.replace(".", ""):
                    return True
        return False

    @staticmethod
    def get_label_name(line):
        try:
            elems = re.split("\s+", line)
            return re.search("^(\w|-)+\.$", elems[1]).group(0)
        except Exception as e:
            print(e)
            print(f"not found label name: {line}")
            sys.exit(1)

    def is_PERFORM_LOOP(self, idx):
        """
        identify is there a PERFORM loop around the given line No in current section
        1) PERFORM VARYING ... UNTIL ... END-PERFORM
        a. Check the following lines for " END-PERFORM" and need to confirm that don't encounter the label and section
         and another perform loop
        b. if a. is found, check the former lines for "PERFORM ... UNTIL"

        2) PERFORM VARYING ... UNTIL ...
        ex. Gr5reien: KS24
        """
        # pattern 2)
        if self.is_perform_start(self.text[idx:idx + 3]):
            return True
        # Scan forward to find " END-PERFORM", making sure we do not encounter labels or sections or another perform loop
        perform_end = idx
        while perform_end < len(self.text) and " END-PERFORM" not in self.text[perform_end]:
            if LoopAnalyzer.is_label_line(self.text[perform_end]) or " SECTION." in self.text[perform_end] or self.is_perform_start(
                    self.text[perform_end:perform_end + 3]):
                return False
            perform_end += 1

        if perform_end < len(self.text) and " END-PERFORM" in self.text[perform_end]:
            # Scan backward to find the corresponding " PERFORM "
            perform_start = idx
            while perform_start > 0 and not LoopAnalyzer.is_label_line(self.text[perform_start]) \
                    and " SECTION." not in self.text[perform_start] \
                    and not self.is_perform_start(self.text[perform_start:perform_start + 3]):
                perform_start -= 1

            if self.is_perform_start(self.text[perform_start:perform_start + 3]):
                # Validate loop start and capture if valid
                return True
            else:
                raise RuntimeError("Can't find perform start!!")
        return False

    def is_perform_start(self, lines):
        # UNTIL [content]  or UNTIL([content])
        return re.search("\sPERFORM\s", lines[0]) and any(re.search("\sUNTIL(\s|\()", line) for line in lines)

    def identify_all_loop(self, cmd):
        idxs = FileManager.get_str_idxs(self.text, cmd)
        # every idx represents a route, ex.: XDBMCR->sectionA->...->MAIN
        for idx in idxs:
            sec_name, _ = SectionAnalyzer.get_section(self.text, idx)
            # if found before, skip
            if self.loop_dict.get(sec_name):
                continue
            is_goto = self.is_GOTO_loop(idx)
            is_perf = self.is_PERFORM_LOOP(idx)
            self.loop_dict[sec_name] = self.def_loop_value(is_goto, is_perf)
            if self.parents_dict[sec_name]:
                perform_sec_str = f"\sPERFORM\s+{sec_name}(\.)?\s"
                self.identify_all_loop(perform_sec_str)

    def def_loop_value(self, is_goto, is_perf):
        if is_goto and is_perf:
            return "PERFORMGOTO"
        elif is_goto:
            return "GOTO"
        elif is_perf:
            return "PERFORM"
        else:
            return None

