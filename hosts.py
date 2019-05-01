#!/usr/bin/python

HOSTS = {
         'taurus': {'type' : 'deploy', 'metadata': False, 'team': ['team_y']},
         'polaris': {'type' : 'deploy', 'metadata': False, 'team': ['team_y']},
         'aries': {'type' : 'non-deploy', 'metadata': True, 'team': ['team_y']},
         'saturn': {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y']},
         'gemini': {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y']},
         'leo': {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y']},

         'rhodes' :  {'type' : 'deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'athens' : {'type' : 'non-deploy', 'metadata': True, 'team': ['team_y', 'team_null']},
         'corfu' : {'type' : 'non-deploy', 'metadata': True, 'team': ['team_y', 'team_null']},
         'sparta' : {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'delphi' : {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'saloniki' : {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'argos' : {'type' : 'non-deploy', 'metadata': True, 'team': ['team_y', 'team_null']},

         'catania' : {'type' : 'deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'rome' : {'type' : 'deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'florence' : {'type' : 'deploy', 'metadata': False, 'team': ['team_y', 'team_null']},

         'naples' : {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'rimini' : {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'genoa' : {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'milan' : {'type' : 'non-deploy', 'metadata': False, 'team': ['team_y', 'team_null']},
         'thebes' : {'type' : 'non-deploy', 'metadata': False, 'team': []},
         'bari' : {'type' : 'non-deploy', 'metadata': False, 'team': []},

         'trump': {'type' : 'deploy',  'metadata': False, 'team': ['team_null']},
         'libra': {'type' : 'deploy', 'metadata': False, 'team': ['team_null']},
         'pegasus': {'type' : 'non-deploy', 'metadata': False, 'team': ['team_null']},
         'moon': {'type' : 'non-deploy', 'metadata': False, 'team': ['team_null']},
         'ursa': {'type' : 'non-deploy', 'metadata': False, 'team': ['team_null']},
         'pluto': {'type' : 'non-deploy', 'metadata': False, 'team': ['team_null']},

         'led' : {'type' : 'physical', 'metadata' : True, 'team': ['physical']},
         'kiss' : {'type' : 'physical', 'metadata' : True, 'team': ['physical']},
         'oasis' : {'type' : 'physical', 'metadata' : True, 'team': ['']},
         'ringo' : {'type' : 'physical', 'metadata' : True, 'team': ['physical']},

}

