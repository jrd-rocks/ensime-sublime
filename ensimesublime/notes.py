from .paths import normalize_path


# Make it smarter
class Note(object):
    def __init__(self, m):
        self.message = m['msg']
        self.file_name = m['file']
        self.severity = m['severity']
        self.start = m['beg']
        self.end = m['end']
        self.line = m['line']
        self.col = m['col']


class NotesStorage(object):
    def __init__(self):
        self.normalized_cache = {}
        self.per_file_cache = {}

    def append(self, data):
        data = list(data)
        for datum in data:
            if datum.file_name not in self.normalized_cache:
                self.normalized_cache[datum.file_name] = normalize_path(datum.file_name)
            file_name = self.normalized_cache[datum.file_name]
            if file_name not in self.per_file_cache:
                self.per_file_cache[file_name] = []
            self.per_file_cache[file_name].append(datum)

    def filter_files(self, pred):
        filenames = self.per_file_cache.keys()
        dropouts = list(normalize_path(filename) for filename in filenames if not pred(filename))
        for file_name in list(self.per_file_cache):
            if file_name in dropouts:
                del self.per_file_cache[file_name]

    # requires self.data
    # def filter_notes(self, pred):
    #     dropouts = set(self.normalized_cache[n.file_name] for n in (m for m in self.data if not pred(m)))
    #     # doesn't take into account pathological cases when a "*.scala" file
    #     # is actually a symlink to something without a ".scala" extension
    #     for file_name in list(self.per_file_cache):
    #         if file_name in dropouts:
    #             del self.per_file_cache[file_name]

    def clear(self):
        # self.filter(lambda f: False)
        self.per_file_cache = {}

    def for_file(self, file_name):
        if file_name not in self.normalized_cache:
            self.normalized_cache[file_name] = normalize_path(file_name)
        file_name = self.normalized_cache[file_name]
        if file_name not in self.per_file_cache:
            self.per_file_cache[file_name] = []
        return self.per_file_cache[file_name]
