pipeline {
    agent any
    environment {
        network_name = "n_${BUILD_ID}_${JENKINS_NODE_COOKIE}"
        container_name = "c_${BUILD_ID}_${JENKINS_NODE_COOKIE}"
        work_branches = "${GIT_BRANCH} ${CHANGE_BRANCH} master"
    }

    stages {
        stage("Pulling docker image") {
            steps {
                script {
                    sh """
                    docker pull lsstts/develop-env:master
                    """
                }
            }
        }
        stage("Preparing environment") {
            steps {
                script {
                    sh """
                    docker network create \${network_name}
                    chmod -R a+rw \${WORKSPACE}
                    container=\$(docker run -v \${WORKSPACE}:/home/saluser/repo/ -td --rm --net \${network_name} --name \${container_name} lsstts/develop-env:master)
                    """
                }
            }
        }
        stage("Checkout sal") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_sal && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout salobj") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_salobj && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout xml") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_xml && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout IDL") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_idl && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_simactuators") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_simactuators && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }

        stage("Checkout ts_scriptqueue") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_scriptqueue && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }


        stage("Checkout ts_ATDomeTrajectory") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_ATDomeTrajectory && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }

        stage("Checkout ts_ATDome") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_ATDome && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_externalscripts") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_externalscripts && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_ATMCSSimulator") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_ATMCSSimulator && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Checkout ts_config_attcs") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repos/ts_config_attcs && /home/saluser/.checkout_repo.sh \${work_branches} && git pull\"
                    """
                }
            }
        }
        stage("Build IDL files") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && setup ts_sal -t current && make_idl_files.py ATAOS ATArchiver ATBuilding ATCamera ATDome ATDomeTrajectory ATHeaderService ATHexapod ATMCS ATMonochromator ATPneumatics ATPtg ATSpectrograph ATWhiteLight CBP CCArchiver CCCamera CCHeaderService CatchupArchiver DIMM DSM Dome EAS Electrometer Environment FiberSpectrograph GenericCamera Hexapod IOTA LOVE LinearStage MTAOS MTAlignment MTArchiver MTCamera MTDomeTrajectory MTHeaderService MTMount MTPtg Rotator Scheduler Script ScriptQueue SummitFacility Test TunableLaser Watcher\"
                    """
                }
            }
        }
        stage("Running tests") {
            steps {
                script {
                    sh """
                    docker exec -u saluser \${container_name} sh -c \"source ~/.setup.sh && cd /home/saluser/repo/ && eups declare -r . -t saluser && setup ts_standardscripts -t saluser && export LSST_DDS_IP=192.168.0.1 && printenv LSST_DDS_IP && py.test --junitxml=tests/.tests/junit.xml\"
                    """
                }
            }
        }
    }
    post {
        always {
            // The path of xml needed by JUnit is relative to
            // the workspace.
            junit 'tests/.tests/junit.xml'

            // Publish the HTML report
            publishHTML (target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'tests/.tests/',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
              ])
        }
        cleanup {
            sh """
                docker exec -u root --privileged \${container_name} sh -c \"chmod -R a+rw /home/saluser/repo/ \"
                docker stop \${container_name} || echo Could not stop container
                docker network rm \${network_name} || echo Could not remove network
            """
            deleteDir()
        }
    }
}
