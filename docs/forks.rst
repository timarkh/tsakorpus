Forks
=====

Introduction
------------

Tsakorpus is regularly updated: new features are introduced, bugs are fixed, etc. If you are going to make your corpus publicly available and maintain it, you will probably want to update its interface once a while to keep it up to date. Since your Tsakorpus instance contains settings and files specific for your corpus, such as ``/conf/corpus.json`` or customized translations in ``/search/web_app/translations``, you will not be able to simply overwrite your files with those taken from a newer version of Tsakorpus.

A solution to that problem is creating a fork. A fork is basically a copy of a repository that lives on its own once it has been created. However, Tsakorpus is stored in a public repository, while you would probably want to keep your project in a private one (especially if you are going to store copyright-protected source files there). Github `does not allow <https://github.community/t/how-to-create-a-private-fork-from-a-public-repo-directly-without-using-cli/2476>`_ private forks of public repositories. However, if you want to host your project repository on Github as well, there is a workaround for that.

Creating a private "fork" on Github
-----------------------------------

Instead of creating a real fork, you can duplicate Tsakorpus repository and manually set up an upstream for it. This is how it is done:

1. Log in to Github.

2. Create a new project by importing Tsakorpus `here <https://github.com/new/import>`_. Put Tsakorpus Github URL (``https://github.com/timarkh/tsakorpus.git``) to the *clone URL* text box. Pick a repository name. Check the "Private" button, unless you want all your corpus files to be visible to anyone. Press "Begin import".

3. Clone the repository to the computer where you are going to work with the corpus.

4. Run the following commands in the folder where you cloned it::

    git remote add upstream https://%YOUR_GITHUB_USERNAME%@github.com/timarkh/tsakorpus.git
    git remote set-url --push upstream DISABLE

5. Add a ``corpus`` folder to ``/src_convertors`` and put all your source files and metadata there, as well as conversion settings (see :doc:`src_convertors`).

6. Adjust settings in ``/conf`` (see :doc:`configuration`) and the interface translations in ``/search/web_app/translations`` (you should at least write the title of your corpus there; see :doc:`interface_languages`).

7. Remove the ``/src_convertors/corpus/**`` line from the ``.gitignore`` file, so that your corpus files can become part of the repository. If you only want to store the source corpus files (e.g. txt or ELAN transcriptions), but not the converted JSONs, you can modify ``.gitignore`` by including ``src_convertors/corpus/json/**``. This usually makes sense because JSONs can be automatically generated from your source files.

After you are through with these steps, you can commit changes and continue working with the corpus. However, if you are familiar with shell scripts or a programming language like Python, it would make sense to add a script that would do all preprocessing steps for you. First of all, that means launching the right convertor on your source files and then moving the output to ``/corpus/%CORPUS_NAME%``. However, depending on the particularities of your corpus, it could do other preprocessing steps, e.g. compiling a word list and analyzing it before launching the source convertor. This way, you will save time on routine operations you need to perform every time before updating the corpus.

Updating the fork
-----------------

If the Tsakorpus repository (which is called an *upstream* repository with respect to your fork) has been updated, you can fetch the changes by running the following commands in the repository folder::

    git fetch upstream
    git rebase upstream/master -Xtheirs
    git push -f origin master

You can also use ``merge`` instead of ``rebase``. Make sure to `resolve all conflicts <https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/resolving-a-merge-conflict-using-the-command-line>`_ before you proceed.

After this operation, you will have to pull changes to the server where your corpus is stored and reload apache (or whatever you use as the web server). Major changes might also require reindexing the corpus first.
