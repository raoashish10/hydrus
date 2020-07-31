"""Helper functions for Item Collection"""

import json
from functools import partial

from flask import Response, jsonify, request, abort
from hydra_python_core.doc_writer import HydraStatus, HydraError

from hydrus.data import crud
from hydrus.data.exceptions import (
    ClassNotFound,
    InstanceExists,
    PropertyNotFound,
    InstanceNotFound,
    PageNotFound,
    InvalidSearchParameter,
    OffsetOutOfRange,
    PropertyNotGiven
)

from hydrus.helpers import (
    set_response_headers,
    getType,
    hydrafy,
    check_writeable_props,
    add_iri_template,
    finalize_response,
    get_link_props,
    error_response,
    send_update,
    validate_object
)

from hydrus.utils import (
    get_session,
    get_api_name,
    get_hydrus_server_url,
    get_page_size,
    get_pagination,
    get_collections_and_parsed_classes
)


def item_collection_get_response(path: str) -> Response:
    """
    Handles GET operation on item collection classes.

    :param path: Path for Item Collection
    :type path: str
    :return: Appropriate response for the GET operation.
    :rtype: Response
    """
    search_params = request.args.to_dict()
    collections, parsed_classes = get_collections_and_parsed_classes()
    api_name = get_api_name()
    is_collection = False
    if path in collections:
        collection = collections[path]["collection"]
        class_path = collection.path
        class_type = collection.name
        is_collection = True
    # If endpoint and GET method is supported in the API and class is supported
    if path in parsed_classes:
        class_path = path
        class_type = parsed_classes[path]['class'].title

    try:
        # Get collection details from the database
        # create partial function for crud operation
        crud_response = partial(crud.get_collection, api_name,
                                class_type, session=get_session(),
                                path=path, search_params=search_params,
                                collection=is_collection)
        if get_pagination():
            # Get paginated response
            response = crud_response(paginate=True,
                                     page_size=get_page_size())
        else:
            # Get whole collection
            response = crud_response(paginate=False)
        if path in parsed_classes:
            # no need of IRI templates for collections
            response["search"] = add_iri_template(path=class_path,
                                                  API_NAME=api_name)

        return set_response_headers(jsonify(hydrafy(response, path=path)))

    except (ClassNotFound, PageNotFound, InvalidSearchParameter,
            OffsetOutOfRange) as e:
        error = e.get_HTTP()
        return error_response(error)


def item_collection_put_response(path: str) -> Response:
    """
    Handles PUT operation on item collection classes.

    :param path: Path for Item Collection
    :type path: str
    :return: Appropriate response for the PUT operation.
    :rtype: Response
    """
    object_ = json.loads(request.data.decode('utf-8'))
    collections, parsed_classes = get_collections_and_parsed_classes()
    is_collection = False
    if path in parsed_classes:
        class_path = path
        is_collection = False
        obj_type = getType(path, "PUT")
    elif path in collections:
        collection = collections[path]["collection"]
        class_path = collection.path
        obj_type = collection.name
        is_collection = True
    if validate_object(object_, obj_type, class_path):
        # If Item in request's JSON is a valid object ie. @type is a key in object_
        # and the right Item type is being added to the collection
        try:
            # Insert object and return location in Header
            object_id = crud.insert(object_=object_, session=get_session(),
                                    collection=is_collection)
            headers_ = [
                {"Location": f"{get_hydrus_server_url()}{get_api_name()}/{path}/{object_id}"}]
            status_description = f"Object with ID {object_id} successfully added"
            status = HydraStatus(code=201,
                                 title="Object successfully added",
                                 desc=status_description)
            return set_response_headers(
                jsonify(status.generate()), headers=headers_,
                status_code=status.code)
        except (ClassNotFound, InstanceExists, PropertyNotFound,
                PropertyNotGiven) as e:
            error = e.get_HTTP()
            return error_response(error)
    else:
        error = HydraError(code=400, title="Data is not valid")
        return error_response(error)
