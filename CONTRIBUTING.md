## Filing bugs

The product is `Webtools` and the component is `Air Mozilla`.

The link to file a new bug is:
[https://bugzilla.mozilla.org/enter_bug.cgi?product=Webtools&component=Air%20Mozilla](https://bugzilla.mozilla.org/enter_bug.cgi?product=Webtools&component=Air%20Mozilla)

You only need to fill in the Summary, Description and possibly the URL.
Try to describe as much as possible in your description and remember,
screenshots are usually very helpful.

## Finding open bugs

All open bugs are [listed on Bugzilla](https://bugzilla.mozilla.org/buglist.cgi?product=Webtools&component=Air Mozilla&resolution=---).
The bugs are sorted by priority from P5 to P1 where P1 are the most "urgent".


## Coding style

All python code, that isn't in "vendor", "vendor-local" or "migrations/*"
needs to pass pep8 and pyflakes.

The best tip for checking this is to install `check.py` with:
```
pip install -e git+https://github.com/jbalogh/check.git#egg=check
```

Then, after you have changed some files, just `check.py` and it
will check only the files you have worked on and staged in git.

For python code, we use **4 spaces**.

For javascript code, we use **4 spaces**.


## Pull requests

If you make a change, the best way to have it landed is to make a
pull request on GitHub.

If you make a pull request on bug, paste the URL to the pull request
into the bug as a new comment.
