class AWSInfra {
  regions int
  azs int
}

function InfraQuestion(question: string) -> string {
    client NovaPro
    prompt #"
    Answer the question:
    {{ question }}
    
    {{ ctx.output_format }}
  "#
}