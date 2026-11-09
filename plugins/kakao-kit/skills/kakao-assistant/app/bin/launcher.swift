// 카톡 비서 실행기: 자기 위치 기준 ../run.sh 하나만 실행한다. 전체 디스크 접근 권한은 이 파일에만 준다.
import Foundation
let here = URL(fileURLWithPath: CommandLine.arguments[0]).resolvingSymlinksInPath().deletingLastPathComponent()
let p = Process()
p.executableURL = URL(fileURLWithPath: "/bin/zsh")
p.arguments = [here.deletingLastPathComponent().appendingPathComponent("run.sh").path]
p.environment = ["HOME": NSHomeDirectory(), "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "ko_KR.UTF-8"]
try p.run()
p.waitUntilExit()
exit(p.terminationStatus)
