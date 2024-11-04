from src import getUrls, downloadRepos, RefactoringMining, DiffMining, TLOCMining, DevelopperEffort, BugFixing
import os
import time

if not os.path.exists('repos'):
    os.mkdir('repos')
if not os.path.exists('results'):
    os.mkdir('results')

# getUrls.run()
# downloadRepos.run()
RefactoringMining.run()
DiffMining.run()
TLOCMining.run()
DevelopperEffort.run()
BugFixing.run()