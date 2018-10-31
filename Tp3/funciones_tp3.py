import numpy as np

import networkx as nx
from networkx import NetworkXError
from networkx.algorithms.community.community_utils import is_partition
from itertools import product
from networkx.readwrite.gml import read_gml
from histograma import histograma


import igraph as igraph

#%%
def formatear_particion(nodos, labels):
    """Dada una partición representada de manera no deseada,
    devuelve una lista de listas en la que cada sublista contiene
    los nombres de los nodos que pertenecen a una cierta comunidad.
    
    nodos : list
        Lista con los nombres de cada nodo
    labels : list
        Lista con las etiquetas de las comunidades a las que pertenece cada
        nodo.
    """
    
    output = []
    labels = np.array(labels)
    for label in set(labels):
        indices_cluster = np.where(labels == label)[0].tolist()
        cluster = [nodos[i] for i in indices_cluster]
        output.append(cluster)
    return output


def calcular_particion(nx_Graph, method="infomap", out_format='listadelistas'):
    """
    Calcula el agrupamiento en comunidades de un grafo.
    
    In:
        nx_Graph: grafo de networkx
        method: metodo de clustering, puede ser: "infomap", "fastgreedy", "eigenvector", "louvain", "edge_betweenness","label_prop", "walktrap", ""
        
    Out:
        labels_dict: diccionario de nodo : a label al cluster al que pertenece.
    """
    if method == "edge_betweenness":
        nx_Graph = max(nx.connected_component_subgraphs(nx_Graph), key=len)#se queda con la componente más grande.
        print("AVISO: restringiendo a la componente connexa más grade. De otro modo falla el algoritmo de detección de comunidades edge_betweenness.")
    
    isdirected = nx.is_directed(nx_Graph)
    np_adj_list = nx.to_numpy_matrix(nx_Graph)
    g = igraph.Graph.Weighted_Adjacency(np_adj_list.tolist(),mode=igraph.ADJ_UPPER)
   
    if method=="infomap":
        labels = g.community_infomap(edge_weights="weight").membership
    if method=="label_prop":
        labels = g.community_label_propagation(weights="weight").membership
    if method=="fastgreedy":
        labels = g.community_fastgreedy(weights="weight").as_clustering().membership
    if method=="eigenvector":
        labels = g.community_leading_eigenvector(weights="weight").membership
    if method=="louvain":
        labels = g.community_multilevel(weights="weight").membership
    if method=="edge_betweenness":
        labels = g.community_edge_betweenness(weights="weight", directed=isdirected).as_clustering().membership
    if method=="walktrap":
        labels = g.community_walktrap(weights="weight").as_clustering().membership
    
    nodos = list(nx_Graph.nodes())
    if out_format == 'listadelistas':
        output = formatear_particion(nodos, labels)
    elif out_format == 'dict':
        output = {node:label for node,label in zip(nodos, labels)}
        
    return output



class NotAPartition(NetworkXError):
    """Raised if a given collection is not a partition.

    """

    def __init__(self, G, collection):
        msg = '{} is not a valid partition of the graph {}'
        msg = msg.format(G, collection)
        super(NotAPartition, self).__init__(msg)


def calcular_modularidad(G, communities, weight='weight'):
    r"""Returns the modularity of the given partition of the graph.

    Modularity is defined in [1]_ as

    .. math::

        Q = \frac{1}{2m} \sum_{ij} \left( A_{ij} - \frac{k_ik_j}{2m}\right)
            \delta(c_i,c_j)

    where $m$ is the number of edges, $A$ is the adjacency matrix of
    `G`, $k_i$ is the degree of $i$ and $\delta(c_i, c_j)$
    is 1 if $i$ and $j$ are in the same community and 0 otherwise.

    Parameters
    ----------
    G : NetworkX Graph

    communities : list
        List of sets of nodes of `G` representing a partition of the
        nodes.

    Returns
    -------
    Q : float
        The modularity of the paritition.

    Raises
    ------
    NotAPartition
        If `communities` is not a partition of the nodes of `G`.

    Examples
    --------
    >>> G = nx.barbell_graph(3, 0)
    >>> nx.algorithms.community.modularity(G, [{0, 1, 2}, {3, 4, 5}])
    0.35714285714285704

    References
    ----------
    .. [1] M. E. J. Newman *Networks: An Introduction*, page 224.
       Oxford University Press, 2011.

    """
    if not is_partition(G, communities):
        raise NotAPartition(G, communities)

    multigraph = G.is_multigraph()
    directed = G.is_directed()
    m = G.size(weight=weight)
    if directed:
        out_degree = dict(G.out_degree(weight=weight))
        in_degree = dict(G.in_degree(weight=weight))
        norm = 1 / m
    else:
        out_degree = dict(G.degree(weight=weight))
        in_degree = out_degree
        norm = 1 / (2 * m)

    def val(u, v):
        try:
            if multigraph:
                w = sum(d.get(weight, 1) for k, d in G[u][v].items())
            else:
                w = G[u][v].get(weight, 1)
        except KeyError:
            w = 0
        # Double count self-loops if the graph is undirected.
        if u == v and not directed:
            w *= 2
        return w - in_degree[u] * out_degree[v] * norm

    Q = sum(val(u, v) for c in communities for u, v in product(c, repeat=2))
    return Q * norm

def comunidad_a_color(g, lista):
    """
    Funcion para asignar colores a las comunidades. Devuelve una lista con colores
    con el mismo orden que la lista de nodos, para meter en la funcion 
    nx.draw(G, node_color = comunidad_a_color(G, lista)). 
    La lista corresponde a la lista de listas, donde cada sublista corresponde a
    una comunidad.
    
    Input: (g, lista)   (grafo de networkx, lista de listas)
    
    Returns:
            colores   (lista)
    .
    .
    """
    colores_posibles = ['r', 'b', 'g', 'k', 'c', 'y', 'violet',
                        'orange', 'indianred',
                        'darkgray']
    colores_random = np.random.choice(np.arange(len(colores_posibles)), size=len(lista),
                                      replace=False)
    nodos = list(g.nodes())
    colores = list(np.zeros(len(nodos)))
    for i in range(len(lista)):
        for j in range(len(nodos)):
            index = colores_random[i]
            if nodos[j] in lista[i]:
                colores[j] = colores_posibles[index]
    return colores

def indices_to_nodos(graph, lista_de_indices):
    """Dada una lista de numeros enteros como indices, devuelve una lista del
    mismo tamaño reemplazando cada elemento por el nodo correspondientes a
    dicho indice."""
    lista_nueva = []
    lista_nodos = list(graph.nodes())
    for i in lista_de_indices:
        lista_nueva.append(lista_nodos[i])
    return lista_nueva


def indices_to_nodos_particion(graph, particion):
    '''Dada una lista de listas de los indicies de los nodos de una particion,
    devuelve una lista de listas del mismo tamaño reemplazando los indices
    por los nodos correspondientes.'''
    for i in range(len(particion)):
        particion[i] = indices_to_nodos(graph, particion[i])
    return particion



def guardar_particiones(graph_original, N, Numero_de_recableos ,lista_de_metodos):
    ''' Toma el grafo orginal y realiza N recableos de la red. Para cada 
    recableo, calcula las particion de la red segun un metodo de particion
    (por ejemplo, infomap) utilizando la funcion calcular_particiones. La 
    funcion guarda la informacion en un array de N*M, donde N es la cant de
    recableos y M es la cant de metodos para particionar. Cada elemento del
    array es una lista de listas con los clusters de la red. Ademas, para el
    grafo original, devuelve una lista con M elementos, donde cada uno es una
    lista de listas para cada particion.'''
    
    salida_grafo_original = [] 
    for metodo in lista_de_metodos:
        lista_nodos_original = calcular_particion(graph_original, method=metodo)
        salida_grafo_original.append(lista_nodos_original)
   
    
    G = graph_original.copy()    
    salida = []
    for metodo in lista_de_metodos:
        salida_por_rewire = []
        for i in range(Numero_de_recableos): 

            g_rewire = nx.double_edge_swap(G, nswap=N,
                                           max_tries=Numero_de_recableos * 1.5)
            lista_nodos = indices_to_nodos_particion(g_rewire, 
                                           calcular_particion(g_rewire,
                                                              method = metodo))
            salida_por_rewire.append(lista_nodos)
        
        salida.append(salida_por_rewire)
    output_path = 'Tp3/tc03Data/Ej_b_particiones_tomi.npz'
    np.savez(output_path, salida = salida, 
             salida_grafo_original = salida_grafo_original) 
    
def graficar_dist_modularidades(graph, lista_de_clusters, lista_de_metodos, metodo = 0):
    '''Toma un grafo y la gran lista con todas las particiones generadas, para
    todos los metodos(la variable 'lista de clusters').
    Dado un metodo, grafica el histograma de las modularidades para todos
    los recableados y tambien dibuja la modularidad de la red original. '''
    dict_metodos = {}
    for k in range (len(lista_de_metodos)):
        dict_metodos[k] = lista_de_metodos[k] 
    
    modularidades = []
    for i in range (len(lista_de_clusters[metodo])):            
        modularidades.append(calcular_modularidad(graph, rewire[metodo][i]))   
    valor_real = calcular_modularidad(graph, original[metodo])
    fig, ax = histograma(modularidades, bins=15, density=True,
                         titulo=r'{} - Distribución de modularidad bajo $H_0$'
                         .format(lista_de_metodos[metodo]),
                         xlabel='Modularidad')
    ax.axvline(valor_real, color='deeppink',
               label='Valor real = {}'.format(valor_real))
    ax.legend()
    plt.show()
#%%
if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import time

    G = nx.balanced_tree(h=3,r=2)
#    nx.draw(G,with_labels=True)
#    plt.show()
    print('Prueba con infomap')
    particion = calcular_particion(G, method='infomap')
    modularidad = calcular_modularidad(G, particion)
    print('La modularidad es', modularidad)
    colores = comunidad_a_color(G, particion)


    plt.figure(); nx.draw(G, with_labels=True, node_color=colores)
    #%% Pueba de la funcion de particiones (Punto 1-b)
    dolph = read_gml('Tp3/dolphins.gml')    
    lista = ["infomap","label_prop", "fastgreedy", "eigenvector", "louvain"
         , "edge_betweenness", "walktrap"]
    # guardar_particiones(dolph, 200, lista)
    #%%
    npzfile = np.load('Tp3/tc03Data/Ej_b_particiones_tomi.npz')
    rewire = npzfile['salida']
    original = npzfile['salida_grafo_original']
    
    #%% Hay un problema con  Edge Betweenness, chequear.
    for i in [0,1,2,3,4,6]:
        graficar_dist_modularidades(dolph, rewire, lista, metodo = i)
