import pandas as pd

df = pd.read_csv('../data/clean/BITAGAP/csvs/bitagap_copies.csv')
df = df.dropna(subset=['INTERNET_ADDRESS'])
df = df[df['INTERNET_ADDRESS'].str.contains('catalogo.bne.es')]
print(df.head(1))
export_df = df[['COPID', 'RELATED_LIBCALLNO', 'INTERNET_ADDRESS']]
print(export_df)
#export_df.to_csv('bitagap_copies_catalogo_match.csv', index=False)


string = "es:Orden de Santiago de la Espada ~ Orden de Calatrava ~ Orden de N. S. de Montesa ~ Orden de Alcántara… [Concordia acerca de en qué causas los comendadores de las Órdenes Militares pueden ser convenidos ante las justicias seglares y en cuáles causas ante las Justicias de las Órdenes], 1500 ca. ad quem"
string = "Aquí comienza de cómo hubo un santo hombre obispo a quien Dios quiso demostrar en este mundo algunas cosas de las sus poridades, entre las cuales le fue revelado el ánima de su madre, que le dijo según oiréis adelante; e hízolo escribir por que tomásemos ejemplo e hiciésemos buenas obras y amásemos hacer bien a los buenos sacerdotes; ca mucho pueden valer estas santas misas diciéndose así como aquí dirá"
count = len(string)
print(count)