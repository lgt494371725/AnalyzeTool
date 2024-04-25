"""
Author: LIU GUANTING
License: MIT
Version: V1.0

Revision History:
    20240425 -
    1. Change the parameter passing method to reading external files
    2. Add basic logger and Error handler
"""
from FileManager import FileManager
from LoopAnalyzer import LoopAnalyzer
from SectionAnalyzer import SectionAnalyzer
import tqdm
from para import params
import logging


class Application:
    def __init__(self, mapping_dict, input_file, input_type, Grp):
        logger.info("Initializing the Application.")
        try:
            self.output_df = {"COBOL": [], "cmd": [], "parents_dict": [], "loop_dict": [], "loop_counts": []}
            self.file_manager = FileManager(mapping_dict, input_file)
            self.type = input_type
            self.Grp = Grp
            self.input_type = input_type
            self.check_para()
        except Exception as e:
            logger.exception("Failed to initialize the Application.")

    def check_para(self):
        logger.info("Checking parameters.")
        assert self.type in ["copy_book", "XDBMCR", "XDBREF"], "input type wrong!!"
        logger.info("Parameters checked and validated.")

    def run(self):
        logging.info("Application started")
        try:
            df = self.file_manager.read_data(Grp=self.Grp, input_type=self.input_type)
            self.file_manager.build_member_dict()
            not_found_list = []
            for index, row in tqdm.tqdm(df.iterrows(), total=df.shape[0]):
                assert row["Gr"] and row["cmd"] and row["COBOL"], "Data structure error!!"
                text = self.file_manager.get_file_content(row["Gr"], row["COBOL"])
                if not text:
                    not_found_list.append(f"Gr:{row['Gr']},file:{row['COBOL']}")
                    continue
                logger.info(f"Grp:{row['Gr']}, COBOL: {row['COBOL']}, cmd: {row['cmd']}")
                # preprocess
                text = FileManager.remove_comment_line(text)
                text = FileManager.remove_empty_line(text)
                logger.info("Data preprocessing completed successfully.")

                sec_analyzer = SectionAnalyzer(text, row["cmd"])

                # cursively extract the section containing the command and all its parent sections
                sections, parents_dict = sec_analyzer.identify_all_rela_section()
                # identify loops
                loop_analyzer = LoopAnalyzer(sections, row["cmd"], parents_dict)
                loop_analyzer.identify_all_loop(row["cmd"])
                loop_counts = loop_analyzer.calc_loop_counts()
                loop_dict = loop_analyzer.get_loop_dict()
                self.collect_results(row, loop_dict, loop_counts, parents_dict)
            FileManager.write_to_file(not_found_list, ".", "not_found_list.txt")
            FileManager.write_to_excel(self.output_df, "results.xlsx")
        except Exception as e:
            logger.error("An error occurred during the Application run: {}".format(e), exc_info=True)

    def collect_results(self, row, loop_dict, loop_counts, parents_dict):
        self.output_df["COBOL"].append(row["COBOL"])
        self.output_df["loop_dict"].append(str(loop_dict))
        self.output_df["loop_counts"].append(loop_counts)
        self.output_df["parents_dict"].append(str(parents_dict))
        self.output_df["cmd"].append(row["cmd"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filename='app.log',
                        filemode='w')
    logger = logging.getLogger(__name__)
    app = Application(**params)
    app.run()
