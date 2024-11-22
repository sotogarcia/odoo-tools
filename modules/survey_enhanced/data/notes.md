## res.groups

| External ID                           | res_id |
| ------------------------------------- | ------ |
| survey.group_survey_user              |   40   |
| survey.group_survey_manager           |   41   |

## module.category

| External ID                           | res_id |
| ------------------------------------- | ------ |
| base.module_category_marketing_survey |   31   |

| external_id                                         | model                  | name                                                                           | domain_force                                           | perm_read | perm_write | perm_create | perm_unlink | global | res_id
| --------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------ | --------- | ---------- | ----------- | ----------- | ------ | ------
| survey.survey_label_rule_survey_manager             | survey.label           | Survey label: manager: all                                                     | [(1, '=', 1)]                                          | x         | x          | x           | x           | f      | 131   
| survey.survey_label_rule_survey_user_read           | survey.label           | Survey label: officer: read all                                                | [(1, '=', 1)]                                          | x         |            |             |             | f      | 132   
| survey.survey_label_rule_survey_user_cw             | survey.question        | Survey label: officer: create/write/unlink linked to own survey only           | [('survey_id.create_uid', '=', user.id)]               |           | x          | x           | x           | f      | 133   
| survey.survey_question_rule_survey_manager          | survey.question        | Survey question: manager: all                                                  | [(1, '=', 1)]                                          | x         | x          | x           | x           | f      | 128   
| survey.survey_question_rule_survey_user_read        | survey.question        | Survey question: officer: read all                                             | [(1, '=', 1)]                                          | x         |            |             |             | f      | 129   
| survey.survey_question_rule_survey_user_cw          | survey.question        | Survey question: officer: create/write/unlink linked to own survey only        | [('survey_id.create_uid', '=', user.id)]               |           | x          | x           | x           | f      | 130   
| survey.survey_survey_rule_survey_manager            | survey.survey          | Survey: manager: all                                                           | [(1, '=', 1)]                                          | x         | x          | x           | x           | f      | 125   
| survey.survey_survey_rule_survey_user_read          | survey.survey          | Survey: officer: read all                                                      | [(1, '=', 1)]                                          | x         |            |             |             | f      | 126   
| survey.survey_survey_rule_survey_user_cwu           | survey.survey          | Survey: officer: create/write/unlink own only                                  | [('create_uid', '=', user.id)]                         |           | x          | x           | x           | f      | 127   
| survey.survey_user_input_rule_survey_manager        | survey.user_input      | Survey user input: manager: all                                                | [(1, '=', 1)]                                          | x         | x          | x           | x           | f      | 134   
| survey.survey_user_input_rule_survey_user_read      | survey.user_input      | Survey user input: officer: read all                                           | [(1, '=', 1)]                                          | x         |            |             |             | f      | 135   
| survey.survey_user_input_rule_survey_user_cw        | survey.user_input      | Survey user input: officer: create/write/unlink linked to own survey only      | [('survey_id.create_uid', '=', user.id)]               |           | x          | x           | x           | f      | 136   
| survey.survey_user_input_line_rule_survey_manager   | survey.user_input_line | Survey user input line: manager: all                                           | [(1, '=', 1)]                                          | x         | x          | x           | x           | f      | 137   
| survey.survey_user_input_line_rule_survey_user_read | survey.user_input_line | Survey user input line: officer: read all                                      | [(1, '=', 1)]                                          | x         |            |             |             | f      | 138   
| survey.survey_user_input_line_rule_survey_user_cw   | survey.user_input_line | Survey user input line: officer: create/write/unlink linked to own survey only | [('user_input_id.survey_id.create_uid', '=', user.id)] |           | x          | x           | x           | f      | 139   
