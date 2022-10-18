<?php

$wgSitename = "Philobiblon localhost";

/*******************************/
/* Enable Federated properties */
/*******************************/
#$wgWBRepoSettings['federatedPropertiesEnabled'] = true;

/*******************************/
/* Enables ConfirmEdit Captcha */
/*******************************/
#wfLoadExtension( 'ConfirmEdit/QuestyCaptcha' );
#$wgCaptchaQuestions = [
#  'What animal' => 'dog',
#];

#$wgCaptchaTriggers['edit']          = true;
#$wgCaptchaTriggers['create']        = true;
#$wgCaptchaTriggers['createtalk']    = true;
#$wgCaptchaTriggers['addurl']        = true;
#$wgCaptchaTriggers['createaccount'] = true;
#$wgCaptchaTriggers['badlogin']      = true;

/*******************************/
/* Disable UI error-reporting  */
/*******************************/
#ini_set( 'display_errors', 0 );

# uncomment to enable federated properties with FactGrid
#$wgWBRepoSettings['federatedPropertiesEnabled'] = true;
#$wgWBRepoSettings['federatedPropertiesSourceScriptUrl'] = 'https://database.factgrid.de/w/';

$wgWBRepoSettings['string-limits'] = [
    'multilang' => [
        'length' => 250,
    ],
    'VT:monolingualtext' => [
        'length' => 400,
    ],
    'VT:string' => [
        'length' => 1500,
    ],
    'PT:url' => [
        'length' => 500,
    ],
];
