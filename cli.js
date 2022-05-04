const project = require('./index.js');
const argParse = require('subheaven-arg');

argParse.init("subheaven-npm-base", "Cumprimenta alguém");
argParse.positional("name", "Nome a ser cumprimentado", { required: true, default: "", sample: "SubHeaven" });
(async() => {
    if (argParse.validate()) {
        await project.hello(`Hello ${params.name}!`);
    }
})();