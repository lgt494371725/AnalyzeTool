import os
import re
import pandas as pd
import logging


logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self, mapping_dict, input_file):
        """
        mapping_dict: {key1: {key2: value}}
        key1 = Grp, key2=member_name, value=file_name
        """
        self.mapping_dict = mapping_dict
        self.member_dict = {grp: dict() for grp in mapping_dict.keys()}
        self.input_file = input_file
        logger.info("FileManager initialized successfully")

    def build_member_dict(self):
        """
        データ断面が異なることにより、ライブラリ名を参照せず、メンバー名を基準とする
        member_dict = {[Gr]:{[member_name]:[file_name]}
        """
        logger.info("Building member dictionary")
        for key, folder in self.mapping_dict.items():
            for root, dirs, files in os.walk(folder):
                for filename in files:
                    parts = filename.split('%')
                    if parts:
                        member_name = parts[-1].replace(".txt", "").replace(".cob", "")
                        self.member_dict[key][member_name] = os.path.join(root, filename)
        logger.info("Member dictionary built successfully")

    def read_data(self, Grp, input_type):
        logger.info("Reading data for group: %s and type: %s", Grp, input_type)
        try:
            match input_type:
                case "copy_book":
                    return self.read_COPY_book(Grp=Grp)
                case "XDBMCR":
                    return self.read_XDBMCR_data(Grp=Grp)
                case "XDBREF":
                    return self.read_XDBREF_data(Grp=Grp)
            logger.info("Data read successfully for %s", Grp)
        except Exception as e:
            logger.error("Failed to read data for %s and %s", Grp, input_type, exc_info=True)

    def read_XDBMCR_data(self, Grp):
        Grp = str(Grp)
        df = pd.read_excel(self.input_file, sheet_name="XDBMCR")
        df = df.rename({"命令": "cmd"}, axis=1)
        df = df[["Gr", "COBOL", "cmd"]]
        # filter grp
        df = df[df["Gr"].astype(str).str.contains(Grp)]
        # filter cmd
        df = df.query('cmd in ["GET-NEXT","GET-XNXT","GET-HNXT","GET-INXT"]')
        print("data size before remove duplicate:", df.shape[0])
        df = df.drop_duplicates()
        print("data size after remove duplicate:", df.shape[0])
        return df

    def read_XDBREF_data(self, Grp):
        Grp = str(Grp)
        df = pd.read_excel(self.input_file, usecols=["Gr", "COBOL"], sheet_name="XDBREF（COBOL）")
        # filter grp
        df = df[df["Gr"].astype(str).str.contains(Grp)]
        print("data size before remove duplicate:", df.shape[0])
        df["cmd"] = "'XDBREF'"
        df = df.drop_duplicates()
        print("data size after remove duplicate:", df.shape[0])
        return df

    def read_COPY_book(self, Grp):
        Grp = str(Grp)
        df = pd.read_excel(self.input_file, sheet_name="COPY句_COBOL")
        df = df[["Gr", "COPY句", "COBOL"]]
        # filter grp
        df = df[df["Gr"].astype(str).str.contains(Grp)]
        df["cmd"] = "\sCOPY\s+" + df["COPY句"] + "\.?\s"
        # filter cmd
        print("data size before remove duplicate:", df.shape[0])
        df = df.drop_duplicates()
        print("data size after remove duplicate:", df.shape[0])
        return df

    def get_file_content(self, Gr, COBOL):
        member_name = COBOL.split("%")[-1].replace(".txt", "")
        Gr = str(Gr)
        assert Gr in self.member_dict.keys()
        if member_name in self.member_dict[Gr].keys():
            file_path = self.member_dict[Gr][member_name]
            return FileManager.read_file(file_path)
        return None

    @staticmethod
    def remove_comment_line(lines):
        new_lines = []
        for line in lines:
            if re.search("^(\d{6}|(\w|%){6})\*", line):
                continue
            new_lines.append(line)
        return new_lines

    @staticmethod
    def remove_empty_line(lines):
        return [line for line in lines if len(line.strip()) > 0]

    @staticmethod
    def read_file(path):
        assert os.path.exists(path), f"{path} not exist!!"
        with open(path, 'r', encoding='SJIS', errors="ignore") as f:
            text = f.read()
            lines = text.split("\n")
        return lines

    @staticmethod
    def write_to_file(text, folder_path, file_name):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'a+', encoding='utf-8') as file:
            text = [i + "\n" for i in text] + ["="*50+"\n"]
            file.writelines(text)

    @staticmethod
    def write_to_excel(dict_, file_name):
        assert type(dict_) == dict, "input type wrong!!"
        output_df = pd.DataFrame(dict_)
        output_df.to_excel(file_name)

    @staticmethod
    def get_str_idxs(text, str):
        return [No for No, line in enumerate(text) if re.search(str, line)]