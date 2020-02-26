## Forks
Tsakorpus is regularly updated: new features are introduced, bugs are fixed, etc. If you are going to make your corpus publicly available and maintain it, you will probably want to update its interface once a while to keep it up to date. Since your tsakorpus instance contains settings and files specific for your corpus, such as ``conf/corpus.json`` or customized translations in ``search/web_app/translations``, you will not be able to simply overwrite your files with those taken from a newer version of tsakorpus.

A solution to that problem is creating a fork. A fork is basically a copy of a repository that lives on its own once it has been created. If you are not familiar with this concept or do not know how a repository can be forked on bitbucket, please read the documentation [here](https://confluence.atlassian.com/bitbucket/forking-a-repository-221449527.html). Good thing about forks on bitbucket is that you can later merge tsakorpus updates into it by clicking one button on the fork's bitbucket page.

### Creating a fork
This is a step-by-step guide to creating a fork for you corpus:

1. Create a fork: log in to bitbucket, go to tsakorpus page, click a plus sign on the left pane and choose "Fork this repository".

2. On the next page, check the "Private repository" checkbox, unless you want all your corpus files to be visible to anyone.

3. Clone the repository to the computer where you are going to work with the corpus.

4. Add a ``corpus`` folder to ``src_convertors`` and put all your source files and metadata there, as well as conversion settings (see ``pipeline.md`` and ``src_convertors.md``).

5. Adjust settings in ``conf`` (see ``configuration.md``) and the interface translations in ``search/web_app/translations`` (you should at least write the title of your corpus there; see ``interface_languages.md``).

6. Remove the ``src_convertors/corpus/\*\*`` line from the ``.gitignore`` file, so that your corpus files can become part of the repository. If you only want to store the source corpus files (e.g. txt or ELAN transcriptions), but not the converted JSONs, you can modify ``.gitignore`` by including ``src_convertors/corpus/json/\*\*``. This usually makes sense because JSONs can be automatically generated from your source files.

After you are through with these steps, you can commit changes and continue working with the corpus. However, if you are familiar with shell scripts or a programming language like python, it would make sense to add a script that would do all preprocessing steps for you. First of all, that means launching the right convertor on your source files and then moving the output to ``corpus/%CORPUS_NAME%``. However, depending on the particularities of your corpus, it could do other preprocessing steps, e.g. compiling a wordlist and analyzing it before launching the source convertor. This way, you will save time on routine operations you need to perform every time before updating the corpus.

### Updating the fork
If the tsakorpus repositiry (which is called an *upstream* repository with respect to your fork) has been updated, you will see a notice on your fork's bitbucket page. A button will appear on the right pane saying "Sync (X commits behind)". If you click it, all recent changes in the upstream repository will be merged into your fork in such a way that no changes you made in the fork are lost. After this operation, you will have to pull changes to the server where your corpus is stored and reload apache (or whatever you use as the web server). Serious changes might also require reindexing the corpus first.