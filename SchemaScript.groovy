import org.identityconnectors.framework.common.objects.ObjectClassInfoBuilder
import org.identityconnectors.framework.common.objects.AttributeInfoBuilder

def logInfo = { msg -> try { log?.info(msg) } catch (ignored) {} }

logInfo("SchemaScript starting")

def ocis = []

// __ACCOUNT__ (what the UI usually treats as the primary object type)
def acc = new ObjectClassInfoBuilder()
acc.setType("__ACCOUNT__")
acc.addAttributeInfo(AttributeInfoBuilder.build("__UID__", String))
acc.addAttributeInfo(AttributeInfoBuilder.build("__NAME__", String))

acc.addAttributeInfo(AttributeInfoBuilder.build("IdAlumno", String))
acc.addAttributeInfo(AttributeInfoBuilder.build("Nombre", String))
acc.addAttributeInfo(AttributeInfoBuilder.build("Apellidos", String))
acc.addAttributeInfo(AttributeInfoBuilder.build("EmailPersonal", String))
acc.addAttributeInfo(AttributeInfoBuilder.build("IdSeguridad", String))
acc.addAttributeInfo(AttributeInfoBuilder.build("Telefono", String))
acc.addAttributeInfo(AttributeInfoBuilder.build("IdPais", String))

ocis.add(acc.build())

// alumnos
def alumnos = new ObjectClassInfoBuilder()
alumnos.setType("alumnos")
alumnos.addAttributeInfo(AttributeInfoBuilder.build("__UID__", String))
alumnos.addAttributeInfo(AttributeInfoBuilder.build("__NAME__", String))

alumnos.addAttributeInfo(AttributeInfoBuilder.build("IdAlumno", String))
alumnos.addAttributeInfo(AttributeInfoBuilder.build("Nombre", String))
alumnos.addAttributeInfo(AttributeInfoBuilder.build("Apellidos", String))
alumnos.addAttributeInfo(AttributeInfoBuilder.build("EmailPersonal", String))
alumnos.addAttributeInfo(AttributeInfoBuilder.build("IdSeguridad", String))
alumnos.addAttributeInfo(AttributeInfoBuilder.build("Telefono", String))
alumnos.addAttributeInfo(AttributeInfoBuilder.build("IdPais", String))

ocis.add(alumnos.build())

// matriculas
def matriculas = new ObjectClassInfoBuilder()
matriculas.setType("matriculas")
matriculas.addAttributeInfo(AttributeInfoBuilder.build("__UID__", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("__NAME__", String))

matriculas.addAttributeInfo(AttributeInfoBuilder.build("IdIntegracionMatricula", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("IdPlan", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("cEstadoMatricula", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("EstadoMatriculaNombre", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("sEstadoMatricula", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("IdAlumno", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("TipoDocumento", String))
matriculas.addAttributeInfo(AttributeInfoBuilder.build("NumeroDocumento", String))

ocis.add(matriculas.build())

return ocis
