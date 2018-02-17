import os


def dir_size(dir_to_calc):
    total_size = 0
    for dir_path, dir_names, file_names in os.walk(dir_to_calc):
        for f in file_names:
            fp = os.path.join(dir_path, f)
            total_size += os.path.getsize(fp)
    return total_size
