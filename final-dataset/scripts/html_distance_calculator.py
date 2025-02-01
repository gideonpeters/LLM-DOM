from zss import simple_distance, Node
from bs4 import BeautifulSoup

class HTMLDistanceCalculator: 
    def __init__(self):
        pass
    
    def assess(self, html1: str, html2: str) -> float:
        tree1 = self.htmlAccessor.parse(html1)
        tree2 = self.htmlAccessor.parse(html2)
        return self.htmlSimilarity.compute(tree1, tree2)
    
    # Function to convert HTML elements into tree nodes
    def html_to_tree(self, element):
        # Base case: If the element is a text node or None, return None
        if element is None or isinstance(element, str):
            return None

        # Create a node with the tag name as label
        node = Node(element.name)

        # Recursively add children for each element's direct descendants
        for child in element.children:
            child_node = self.html_to_tree(child)
            if child_node:
                node.addkid(child_node)
        
        return node

    # Function to calculate tree edit distance between two HTML trees
    def calculate_tree_edit_distance(self, html_file1, html_file2):
        # Parse the HTML files
        with open(html_file1, 'r', encoding='utf-8') as file1:
            html1 = BeautifulSoup(file1, 'html.parser')
        with open(html_file2, 'r', encoding='utf-8') as file2:
            html2 = BeautifulSoup(file2, 'html.parser')

        # Convert HTML to trees
        tree1 = self.html_to_tree(html1.body)
        tree2 = self.html_to_tree(html2.body)

        # Compute tree edit distance
        distance = simple_distance(tree1, tree2)
        
        return distance
    

html_file_1 = "extracted-doms/original/airbnb.html"
html_file_2 = "merged-chunks/original/airbnb.html"

similarity_assessor = HTMLDistanceCalculator()
distance = similarity_assessor.calculate_tree_edit_distance(html_file_1, html_file_2)

print(f"Tree edit distance between the two HTML files: {distance}")