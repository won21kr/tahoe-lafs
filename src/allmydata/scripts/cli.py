import os.path, re, sys, fnmatch
from twisted.python import usage
from allmydata.scripts.common import BaseOptions, get_aliases

NODEURL_RE=re.compile("http://([^:]*)(:([1-9][0-9]*))?")

class VDriveOptions(BaseOptions, usage.Options):
    optParameters = [
        ["node-directory", "d", "~/.tahoe",
         "Look here to find out which Tahoe node should be used for all "
         "operations. The directory should either contain a full Tahoe node, "
         "or a file named node.url which points to some other Tahoe node. "
         "It should also contain a file named private/aliases which contains "
         "the mapping from alias name to root dirnode URI."
         ],
        ["node-url", "u", None,
         "URL of the tahoe node to use, a URL like \"http://127.0.0.1:3456\". "
         "This overrides the URL found in the --node-directory ."],
        ["dir-cap", None, None,
         "Which dirnode URI should be used as the 'tahoe' alias."]
        ]

    def postOptions(self):
        # compute a node-url from the existing options, put in self['node-url']
        if self['node-directory']:
            if sys.platform == 'win32' and self['node-directory'] == '~/.tahoe':
                from allmydata.windows import registry
                self['node-directory'] = registry.get_base_dir_path()
            else:
                self['node-directory'] = os.path.expanduser(self['node-directory'])
        if self['node-url']:
            if (not isinstance(self['node-url'], basestring)
                or not NODEURL_RE.match(self['node-url'])):
                msg = ("--node-url is required to be a string and look like "
                       "\"http://HOSTNAMEORADDR:PORT\", not: %r" %
                       (self['node-url'],))
                raise usage.UsageError(msg)
        else:
            node_url_file = os.path.join(self['node-directory'], "node.url")
            self['node-url'] = open(node_url_file, "r").read().strip()
        if self['node-url'][-1] != "/":
            self['node-url'] += "/"

        aliases = get_aliases(self['node-directory'])
        if self['dir-cap']:
            aliases["tahoe"] = self['dir-cap']
        self.aliases = aliases # maps alias name to dircap


class MakeDirectoryOptions(VDriveOptions):
    def parseArgs(self, where=""):
        self.where = where
    longdesc = """Create a new directory, either unlinked or as a subdirectory."""

class AddAliasOptions(VDriveOptions):
    def parseArgs(self, alias, cap):
        self.alias = alias
        self.cap = cap

    def getSynopsis(self):
        return "%s add-alias ALIAS DIRCAP" % (os.path.basename(sys.argv[0]),)

    longdesc = """Add a new alias for an existing directory."""

class CreateAliasOptions(VDriveOptions):
    def parseArgs(self, alias):
        self.alias = alias

    def getSynopsis(self):
        return "%s create-alias ALIAS" % (os.path.basename(sys.argv[0]),)

    longdesc = """Creates a new directory and adds an alias for it."""

class ListAliasOptions(VDriveOptions):
    longdesc = """Displays a table of all configured aliases."""

class ListOptions(VDriveOptions):
    optFlags = [
        ("long", "l", "Use long format: show file sizes, and timestamps"),
        ("uri", "u", "Show file/directory URIs"),
        ("readonly-uri", None, "Show readonly file/directory URIs"),
        ("classify", "F", "Append '/' to directory names, and '*' to mutable"),
        ("json", None, "Show the raw JSON output"),
        ]
    def parseArgs(self, where=""):
        self.where = where

    longdesc = """List the contents of some portion of the virtual drive."""

class GetOptions(VDriveOptions):
    def parseArgs(self, arg1, arg2=None):
        # tahoe get FOO |less            # write to stdout
        # tahoe get tahoe:FOO |less      # same
        # tahoe get FOO bar              # write to local file
        # tahoe get tahoe:FOO bar        # same

        self.from_file = arg1
        self.to_file = arg2
        if self.to_file == "-":
            self.to_file = None

    def getSynopsis(self):
        return "%s get VDRIVE_FILE LOCAL_FILE" % (os.path.basename(sys.argv[0]),)

    longdesc = """Retrieve a file from the virtual drive and write it to the
    local filesystem. If LOCAL_FILE is omitted or '-', the contents of the file
    will be written to stdout."""

    def getUsage(self, width=None):
        t = VDriveOptions.getUsage(self, width)
        t += """
Examples:
 % tahoe get FOO |less            # write to stdout
 % tahoe get tahoe:FOO |less      # same
 % tahoe get FOO bar              # write to local file
 % tahoe get tahoe:FOO bar        # same
"""
        return t

class PutOptions(VDriveOptions):
    optFlags = [
        ("mutable", "m", "Create a mutable file instead of an immutable one."),
        ]

    def parseArgs(self, arg1=None, arg2=None):
        # cat FILE | tahoe put           # create unlinked file from stdin
        # cat FILE | tahoe put -         # same
        # tahoe put bar                  # create unlinked file from local 'bar'
        # cat FILE | tahoe put - FOO     # create tahoe:FOO from stdin
        # tahoe put bar FOO              # copy local 'bar' to tahoe:FOO
        # tahoe put bar tahoe:FOO        # same

        if arg1 is not None and arg2 is not None:
            self.from_file = arg1
            self.to_file = arg2
        elif arg1 is not None and arg2 is None:
            self.from_file = arg1 # might be "-"
            self.to_file = None
        else:
            self.from_file = None
            self.to_file = None
        if self.from_file == "-":
            self.from_file = None

    def getSynopsis(self):
        return "%s put LOCAL_FILE VDRIVE_FILE" % (os.path.basename(sys.argv[0]),)

    longdesc = """Put a file into the virtual drive (copying the file's
    contents from the local filesystem). If VDRIVE_FILE is missing, upload
    the file but do not link it into a directory: prints the new filecap to
    stdout. If LOCAL_FILE is missing or '-', data will be copied from stdin.
    VDRIVE_FILE is assumed to start with tahoe: unless otherwise specified."""

    def getUsage(self, width=None):
        t = VDriveOptions.getUsage(self, width)
        t += """
Examples:
 % cat FILE | tahoe put                # create unlinked file from stdin
 % cat FILE | tahoe -                  # same
 % tahoe put bar                       # create unlinked file from local 'bar'
 % cat FILE | tahoe put - FOO          # create tahoe:FOO from stdin
 % tahoe put bar FOO                   # copy local 'bar' to tahoe:FOO
 % tahoe put bar tahoe:FOO             # same
 % tahoe put bar MUTABLE-FILE-WRITECAP # modify the mutable file in-place
"""
        return t

class CpOptions(VDriveOptions):
    optFlags = [
        ("recursive", "r", "Copy source directory recursively."),
        ("verbose", "v", "Be noisy about what is happening."),
        ("caps-only", None,
         "When copying to local files, write out filecaps instead of actual "
         "data. (only useful for debugging and tree-comparison purposes)"),
        ]
    def parseArgs(self, *args):
        if len(args) < 2:
            raise usage.UsageError("cp requires at least two arguments")
        self.sources = args[:-1]
        self.destination = args[-1]
    def getSynopsis(self):
        return "Usage: tahoe [options] cp FROM.. TO"
    longdesc = """
    Use 'tahoe cp' to copy files between a local filesystem and a Tahoe
    virtual filesystem. Any FROM/TO arguments that begin with an alias
    indicate Tahoe-side files, and arguments which do not indicate local
    files. Directories will be copied recursively. New Tahoe-side directories
    will be created when necessary. Assuming that you have previously set up
    an alias 'home' with 'tahoe create-alias home', here are some examples:

    tahoe cp ~/foo.txt home:  # creates tahoe-side home:foo.txt

    tahoe cp ~/foo.txt /tmp/bar.txt home:  # copies two files to home:

    tahoe cp ~/Pictures home:stuff/my-pictures  # copies directory recursively

    You can also use a dircap as either FROM or TO:

    tahoe cp URI:DIR2-RO:j74uhg25nwdpjpacl6rkat2yhm:kav7ijeft5h7r7rxdp5bgtlt3viv32yabqajkrdykozia5544jqa/wiki.html ./   # copy Zooko's wiki page to a local file

    This command still has some limitations: symlinks, special files (device
    nodes, named pipes), and non-ASCII filenames are not handled very well.
    Arguments should probably not have trailing slashes. 'tahoe cp' does not
    behave as much like /bin/cp as you would wish, especially with respect to
    trailing slashes.
    """

class RmOptions(VDriveOptions):
    def parseArgs(self, where):
        self.where = where

    def getSynopsis(self):
        return "%s rm VDRIVE_FILE" % (os.path.basename(sys.argv[0]),)

class MvOptions(VDriveOptions):
    def parseArgs(self, frompath, topath):
        self.from_file = frompath
        self.to_file = topath

    def getSynopsis(self):
        return "%s mv FROM TO" % (os.path.basename(sys.argv[0]),)

class LnOptions(VDriveOptions):
    def parseArgs(self, frompath, topath):
        self.from_file = frompath
        self.to_file = topath

    def getSynopsis(self):
        return "%s ln FROM TO" % (os.path.basename(sys.argv[0]),)

class BackupConfigurationError(Exception):
    pass

class BackupOptions(VDriveOptions):
    optFlags = [
        ("verbose", "v", "Be noisy about what is happening."),
        ("ignore-timestamps", None, "Do not use backupdb timestamps to decide if a local file is unchanged."),
        ]

    vcs_patterns = ('CVS', 'RCS', 'SCCS', '.git', '.gitignore', '.cvsignore', '.svn',
                   '.arch-ids','{arch}', '=RELEASE-ID', '=meta-update', '=update',
                   '.bzr', '.bzrignore', '.bzrtags', '.hg', '.hgignore', '_darcs')

    def __init__(self):
        super(BackupOptions, self).__init__()
        self['exclude'] = set()

    def parseArgs(self, localdir, topath):
        self.from_dir = localdir
        self.to_dir = topath

    def getSynopsis(Self):
        return "%s backup FROM ALIAS:TO" % os.path.basename(sys.argv[0])

    def opt_exclude(self, pattern):
        """Ignore files matching a glob pattern. You may give multiple
        '--exclude' options."""
        g = pattern.strip()
        if g:
            exclude = self['exclude']
            exclude.add(g)

    def opt_exclude_from(self, filepath):
        """Ignore file matching glob patterns listed in file, one per
        line."""
        try:
            exclude_file = file(filepath)
        except:
            raise BackupConfigurationError('Error opening exclude file %r.' % filepath)
        try:
            for line in exclude_file:
                self.opt_exclude(line)
        finally:
            exclude_file.close()

    def opt_exclude_vcs(self):
        """Exclude files and directories used by following version
        control systems: 'CVS', 'RCS', 'SCCS', 'SVN', 'Arch',
        'Bazaar', 'Mercurial', and 'Darcs'."""
        for pattern in self.vcs_patterns:
            self.opt_exclude(pattern)

    def filter_listdir(self, listdir):
        """Yields non-excluded childpaths in path."""
        exclude = self['exclude']
        exclude_regexps = [re.compile(fnmatch.translate(pat)) for pat in exclude]
        for filename in listdir:
            for regexp in exclude_regexps:
                if regexp.match(filename):
                    break
            else:
                yield filename

    longdesc = """Add a versioned backup of the local FROM directory to a timestamped subdir of the (tahoe) TO/Archives directory, sharing as many files and directories as possible with the previous backup. Creates TO/Latest as a reference to the latest backup. Behaves somewhat like 'rsync -a --link-dest=TO/Archives/(previous) FROM TO/Archives/(new); ln -sf TO/Archives/(new) TO/Latest'."""

class WebopenOptions(VDriveOptions):
    def parseArgs(self, where=''):
        self.where = where

    def getSynopsis(self):
        return "%s webopen [ALIAS:PATH]" % (os.path.basename(sys.argv[0]),)

    longdesc = """Opens a webbrowser to the contents of some portion of the virtual drive."""

class ManifestOptions(VDriveOptions):
    optFlags = [
        ("storage-index", "s", "Only print storage index strings, not pathname+cap"),
        ("verify-cap", None, "Only print verifycap, not pathname+cap"),
        ("repair-cap", None, "Only print repaircap, not pathname+cap"),
        ("raw", "r", "Display raw JSON data instead of parsed"),
        ]
    def parseArgs(self, where=''):
        self.where = where

    def getSynopsis(self):
        return "%s manifest [ALIAS:PATH]" % (os.path.basename(sys.argv[0]),)

    longdesc = """Print a list of all files/directories reachable from the given starting point."""

class StatsOptions(VDriveOptions):
    optFlags = [
        ("raw", "r", "Display raw JSON data instead of parsed"),
        ]
    def parseArgs(self, where=''):
        self.where = where

    def getSynopsis(self):
        return "%s stats [ALIAS:PATH]" % (os.path.basename(sys.argv[0]),)

    longdesc = """Print statistics about of all files/directories reachable from the given starting point."""

class CheckOptions(VDriveOptions):
    optFlags = [
        ("raw", None, "Display raw JSON data instead of parsed"),
        ("verify", None, "Verify all hashes, instead of merely querying share presence"),
        ("repair", None, "Automatically repair any problems found"),
        ("add-lease", None, "Add/renew lease on all shares"),
        ]
    def parseArgs(self, where=''):
        self.where = where

    def getSynopsis(self):
        return "%s check [ALIAS:PATH]" % (os.path.basename(sys.argv[0]),)

    longdesc = """Check a single file or directory: count how many shares are available, verify their hashes. Optionally repair the file if any problems were found."""

class DeepCheckOptions(VDriveOptions):
    optFlags = [
        ("raw", None, "Display raw JSON data instead of parsed"),
        ("verify", None, "Verify all hashes, instead of merely querying share presence"),
        ("repair", None, "Automatically repair any problems found"),
        ("add-lease", None, "Add/renew lease on all shares"),
        ("verbose", "v", "Be noisy about what is happening."),
        ]
    def parseArgs(self, where=''):
        self.where = where

    def getSynopsis(self):
        return "%s deep-check [ALIAS:PATH]" % (os.path.basename(sys.argv[0]),)

    longdesc = """Check all files/directories reachable from the given starting point (which must be a directory), like 'tahoe check' but for multiple files. Optionally repair any problems found."""

subCommands = [
    ["mkdir", None, MakeDirectoryOptions, "Create a new directory"],
    ["add-alias", None, AddAliasOptions, "Add a new alias cap"],
    ["create-alias", None, CreateAliasOptions, "Create a new alias cap"],
    ["list-aliases", None, ListAliasOptions, "List all alias caps"],
    ["ls", None, ListOptions, "List a directory"],
    ["get", None, GetOptions, "Retrieve a file from the virtual drive."],
    ["put", None, PutOptions, "Upload a file into the virtual drive."],
    ["cp", None, CpOptions, "Copy one or more files."],
    ["rm", None, RmOptions, "Unlink a file or directory in the virtual drive."],
    ["mv", None, MvOptions, "Move a file within the virtual drive."],
    ["ln", None, LnOptions, "Make an additional link to an existing file."],
    ["backup", None, BackupOptions, "Make target dir look like local dir."],
    ["webopen", None, WebopenOptions, "Open a webbrowser to the root_dir"],
    ["manifest", None, ManifestOptions, "List all files/dirs in a subtree"],
    ["stats", None, StatsOptions, "Print statistics about all files/dirs in a subtree"],
    ["check", None, CheckOptions, "Check a single file or directory"],
    ["deep-check", None, DeepCheckOptions, "Check all files/directories reachable from a starting point"],
    ]

def mkdir(options):
    from allmydata.scripts import tahoe_mkdir
    rc = tahoe_mkdir.mkdir(options)
    return rc

def add_alias(options):
    from allmydata.scripts import tahoe_add_alias
    rc = tahoe_add_alias.add_alias(options)
    return rc

def create_alias(options):
    from allmydata.scripts import tahoe_add_alias
    rc = tahoe_add_alias.create_alias(options)
    return rc

def list_aliases(options):
    from allmydata.scripts import tahoe_add_alias
    rc = tahoe_add_alias.list_aliases(options)
    return rc

def list(options):
    from allmydata.scripts import tahoe_ls
    rc = tahoe_ls.list(options)
    return rc

def get(options):
    from allmydata.scripts import tahoe_get
    rc = tahoe_get.get(options)
    if rc == 0:
        if options.to_file is None:
            # be quiet, since the file being written to stdout should be
            # proof enough that it worked, unless the user is unlucky
            # enough to have picked an empty file
            pass
        else:
            print >>options.stderr, "%s retrieved and written to %s" % \
                  (options.from_file, options.to_file)
    return rc

def put(options):
    from allmydata.scripts import tahoe_put
    rc = tahoe_put.put(options)
    return rc

def cp(options):
    from allmydata.scripts import tahoe_cp
    rc = tahoe_cp.copy(options)
    return rc

def rm(options):
    from allmydata.scripts import tahoe_rm
    rc = tahoe_rm.rm(options)
    return rc

def mv(options):
    from allmydata.scripts import tahoe_mv
    rc = tahoe_mv.mv(options, mode="move")
    return rc

def ln(options):
    from allmydata.scripts import tahoe_mv
    rc = tahoe_mv.mv(options, mode="link")
    return rc

def backup(options):
    from allmydata.scripts import tahoe_backup
    rc = tahoe_backup.backup(options)
    return rc

def webopen(options, opener=None):
    from allmydata.scripts import tahoe_webopen
    rc = tahoe_webopen.webopen(options, opener=opener)
    return rc

def manifest(options):
    from allmydata.scripts import tahoe_manifest
    rc = tahoe_manifest.manifest(options)
    return rc

def stats(options):
    from allmydata.scripts import tahoe_manifest
    rc = tahoe_manifest.stats(options)
    return rc

def check(options):
    from allmydata.scripts import tahoe_check
    rc = tahoe_check.check(options)
    return rc

def deepcheck(options):
    from allmydata.scripts import tahoe_check
    rc = tahoe_check.deepcheck(options)
    return rc

dispatch = {
    "mkdir": mkdir,
    "add-alias": add_alias,
    "create-alias": create_alias,
    "list-aliases": list_aliases,
    "ls": list,
    "get": get,
    "put": put,
    "cp": cp,
    "rm": rm,
    "mv": mv,
    "ln": ln,
    "backup": backup,
    "webopen": webopen,
    "manifest": manifest,
    "stats": stats,
    "check": check,
    "deep-check": deepcheck,
    }
